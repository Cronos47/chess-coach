from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import chess

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from .models import AgentOutput, CoachOutput, MentalOutput, PositionOutput
from .analysis import classify_move_quality_from_swing
from . import chess_engine


# ============================================================
# Tools (plain python functions)
# Passed directly to create_agent(tools=[...])
# ============================================================

# Tool-call context is stored in module globals for simplicity (single-session).
# This allows tools to access the current request's board/state without extra services.
_TOOL_CTX: Dict[str, Any] = {}


def _set_tool_ctx(
    *,
    board: chess.Board,
    move_list: List[str],
    player_side: str,
    bot_difficulty: str,
    coach_verbosity: int,
    signals: Dict[str, Any],
):
    _TOOL_CTX.clear()
    _TOOL_CTX.update(
        {
            "board": board,
            "move_list": move_list,
            "player_side": player_side,
            "bot_difficulty": bot_difficulty,
            "coach_verbosity": coach_verbosity,
            "signals": signals,
        }
    )


def get_current_game_state() -> str:
    """
    Get the current game state for the agent.

    Returns a compact, engine-independent snapshot:
    - FEN
    - move_list (UCI strings)
    - player_side
    - bot_difficulty
    - coach_verbosity
    - mental signals (think times, blunder streak, undo attempts, rapid_after_blunder, self_report)
    """
    board: chess.Board = _TOOL_CTX["board"]
    return (
        f"FEN: {board.fen()}\n"
        f"MoveList(UCI): {_TOOL_CTX['move_list']}\n"
        f"PlayerSide: {_TOOL_CTX['player_side']}\n"
        f"BotDifficulty: {_TOOL_CTX['bot_difficulty']}\n"
        f"CoachVerbosity: {_TOOL_CTX['coach_verbosity']}\n"
        f"Signals: {_TOOL_CTX['signals']}\n"
    )


def engine_analyze(multipv: int = 2, depth: int = 12) -> str:
    """
    Run Stockfish analysis on the current position.

    Args:
      multipv: number of principal variations to request
      depth: search depth

    Returns:
      Text with eval + PV lines. The agent MUST use this tool for eval/PV.
    """
    if chess_engine.ENGINE is None:
        return "ERROR: Engine not initialized"

    board: chess.Board = _TOOL_CTX["board"]
    info = chess_engine.ENGINE.analyze_position(board, depth=depth, multipv=multipv)
    lines = []
    for i, pv in enumerate(info.get("multipv", []), start=1):
        lines.append(f"PV{i}: eval={pv.get('eval_str')} pv={pv.get('pv')}")
    if not lines:
        primary = info.get("primary", {})
        lines.append(f"PV1: eval={primary.get('eval_str')} pv={primary.get('pv')}")
    return "\n".join(lines)


def classify_last_move(eval_before_cp: Optional[int], eval_after_cp: Optional[int]) -> str:
    """
    Classify the player's last move quality based on eval swing.

    The caller should pass:
      eval_before_cp: engine eval in centipawns before the player's last move (from player's POV if possible)
      eval_after_cp: engine eval in centipawns after the player's last move

    Returns:
      One of: Best, Good, Inaccuracy, Mistake, Blunder
    """
    quality = classify_move_quality_from_swing(eval_before_cp, eval_after_cp)
    return quality.label


TOOLS = [get_current_game_state, engine_analyze, classify_last_move]


# ============================================================
# Agent Prompt
# ============================================================

SYSTEM_PROMPT = """You are an Agentic Chess Coach.

You MUST call tools for:
- game state (FEN, move list, signals)
- engine analysis (eval and PV)
- move quality classification (eval swing)

Do NOT invent evaluations or PV lines. Use ONLY tool outputs.

Return STRICTLY these sections in this exact order and format:

[MENTAL_STATE_CHECK]
Observed Signals:
- ...
Inference (non-medical, uncertain):
- ...
10s Micro-Reset Tip:
- ...

[POSITION_SNAPSHOT]
Eval:
- ...
Why:
- ...
Immediate Threats:
- ...
Plans (White):
- ...
Plans (Black):
- ...

[MOVE_QUALITY]
Label:
- Best/Good/Inaccuracy/Mistake/Blunder
Reason:
- short reason grounded in engine + position

[COACHING]
Actionable:
- 1)
- 2)
- 3)
Short PV (4-8 ply max):
- ...

[BOT_MOVE]
Explain:
- why bot's last move (if already played), or next best defense
Next-turn checklist:
- ...
"""


# ============================================================
# Parsing agent text -> structured JSON for UI tabs
# ============================================================

def _section(text: str, tag: str) -> str:
    pattern = rf"\[{re.escape(tag)}\]\s*(.*?)(?=\n\[[A-Z_]+\]|\Z)"
    m = re.search(pattern, text, flags=re.S)
    return m.group(1).strip() if m else ""


def _bullets(block: str) -> List[str]:
    out = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return [b for b in out if b]


def _numbered(block: str) -> List[str]:
    out = []
    for line in block.splitlines():
        line = line.strip()
        if re.match(r"^\d+\)\s+", line):
            out.append(re.sub(r"^\d+\)\s+", "", line).strip())
    return [b for b in out if b]


def parse_agent_report(text: str) -> AgentOutput:
    mental = _section(text, "MENTAL_STATE_CHECK")
    pos = _section(text, "POSITION_SNAPSHOT")
    quality = _section(text, "MOVE_QUALITY")
    coaching = _section(text, "COACHING")

    # --- Mental ---
    obs = []
    inference = ""
    tip = ""

    if mental:
        # Observed Signals bullets
        if "Observed Signals:" in mental:
            after = mental.split("Observed Signals:", 1)[1]
            # up to Inference
            parts = re.split(r"\bInference", after, maxsplit=1)
            obs = _bullets(parts[0])

        m_inf = re.search(r"Inference.*?:\s*(.*?)(?=10s Micro-Reset Tip:|\Z)", mental, flags=re.S)
        if m_inf:
            inference = m_inf.group(1).strip().replace("\n", " ").strip("- ").strip()

        m_tip = re.search(r"10s Micro-Reset Tip:\s*(.*)", mental, flags=re.S)
        if m_tip:
            tip = m_tip.group(1).strip().strip("- ").strip()

    # --- Position ---
    eval_line = ""
    why = []
    threats = []
    plans_white = []
    plans_black = []

    if pos:
        m_eval = re.search(r"Eval:\s*(.*?)(?=\nWhy:|\Z)", pos, flags=re.S)
        if m_eval:
            eval_line = m_eval.group(1).strip().strip("- ").strip()

        m_why = re.search(r"Why:\s*(.*?)(?=\nImmediate Threats:|\Z)", pos, flags=re.S)
        if m_why:
            why = _bullets(m_why.group(1))

        m_thr = re.search(r"Immediate Threats:\s*(.*?)(?=\nPlans \(White\):|\Z)", pos, flags=re.S)
        if m_thr:
            threats = _bullets(m_thr.group(1))

        m_pw = re.search(r"Plans \(White\):\s*(.*?)(?=\nPlans \(Black\):|\Z)", pos, flags=re.S)
        if m_pw:
            plans_white = _bullets(m_pw.group(1))

        m_pb = re.search(r"Plans \(Black\):\s*(.*?)(?=\n|\Z)", pos, flags=re.S)
        if m_pb:
            plans_black = _bullets(m_pb.group(1))

    # --- Move Quality ---
    label = "Good"
    if quality:
        m_label = re.search(r"Label:\s*(.*)", quality)
        if m_label:
            label = m_label.group(1).strip().strip("- ").strip()
            # normalize
            allowed = {"Best", "Good", "Inaccuracy", "Mistake", "Blunder"}
            if label not in allowed:
                label = "Good"

    # --- Coaching ---
    bullets = []
    pv = None
    if coaching:
        m_act = re.search(r"Actionable:\s*(.*?)(?=\nShort PV|\Z)", coaching, flags=re.S)
        if m_act:
            bullets = _numbered(m_act.group(1))
            if not bullets:
                bullets = _bullets(m_act.group(1))
        m_pv = re.search(r"Short PV.*?:\s*(.*)", coaching, flags=re.S)
        if m_pv:
            pv = m_pv.group(1).strip().strip("- ").strip()

    return AgentOutput(
        coach=CoachOutput(move_quality=label, bullets=bullets[:3], pv=pv),
        mental=MentalOutput(
            observed_signals=obs,
            inference=inference or "Uncertain; monitor focus and time usage.",
            micro_reset_tip=tip or "Take one deep breath, relax shoulders, and pick one plan for the next move.",
        ),
        position=PositionOutput(
            eval=eval_line or "unknown",
            why=why or [],
            threats=threats or [],
            plans={"white": plans_white or [], "black": plans_black or []},
        ),
        raw_text=text,
    )


# ============================================================
# Main entry: run_coach_agent
# ============================================================

def run_coach_agent(
    *,
    board: chess.Board,
    move_list: List[str],
    player_side: str,
    bot_difficulty: str,
    coach_verbosity: int,
    signals: Dict[str, Any],
) -> AgentOutput:
    """
    Run the agent after a move. Must be engine-grounded.

    Inputs include full move history + signals so the agent can use prior moves
    (blunder streak, think time, rapid after blunder) in a non-medical inference.
    """
    if not os.getenv("OPENAI_API_KEY"):
        # Graceful degradation: still return something parseable
        raw = (
            "[MENTAL_STATE_CHECK]\n"
            "Observed Signals:\n"
            "- OPENAI_API_KEY missing\n"
            "Inference (non-medical, uncertain):\n"
            "- Coaching disabled until key is set\n"
            "10s Micro-Reset Tip:\n"
            "- Set OPENAI_API_KEY and restart backend\n\n"
            "[POSITION_SNAPSHOT]\n"
            "Eval:\n- unknown\n"
            "Why:\n- engine unavailable\n"
            "Immediate Threats:\n- unknown\n"
            "Plans (White):\n- develop pieces\n"
            "Plans (Black):\n- develop pieces\n\n"
            "[MOVE_QUALITY]\n"
            "Label:\n- Good\n"
            "Reason:\n- no engine eval available\n\n"
            "[COACHING]\n"
            "Actionable:\n"
            "- 1) Set OPENAI_API_KEY\n"
            "Short PV (4-8 ply max):\n"
            "- \n\n"
            "[BOT_MOVE]\n"
            "Explain:\n- \n"
            "Next-turn checklist:\n- \n"
        )
        return parse_agent_report(raw)

    # Set tool context for this invocation
    _set_tool_ctx(
        board=board,
        move_list=move_list,
        player_side=player_side,
        bot_difficulty=bot_difficulty,
        coach_verbosity=coach_verbosity,
        signals=signals,
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    # You required this exact invocation pattern
    agent = create_agent(llm, TOOLS, system_prompt=SYSTEM_PROMPT)

    # Input asks agent to call tools and produce the strict format
    user_input = (
        "Analyze the current game using tools. "
        "Use the move history and mental signals to produce better coaching. "
        "Return the strict sectioned report."
    )

    result = agent.invoke({"input": user_input})

    # LangChain returns a messages list; last message is the model output
    try:
        text = result["messages"][-1].content
    except Exception:
        text = str(result)

    try:
        return parse_agent_report(text)
    except Exception:
        # Fallback: return raw text in all fields
        fallback = (
            "[MENTAL_STATE_CHECK]\nObserved Signals:\n- parse failed\n"
            "Inference (non-medical, uncertain):\n- parse failed\n"
            "10s Micro-Reset Tip:\n- take a breath\n\n"
            "[POSITION_SNAPSHOT]\nEval:\n- unknown\nWhy:\n- unknown\nImmediate Threats:\n- unknown\n"
            "Plans (White):\n- unknown\nPlans (Black):\n- unknown\n\n"
            "[MOVE_QUALITY]\nLabel:\n- Good\nReason:\n- unknown\n\n"
            "[COACHING]\nActionable:\n- 1) See raw output\nShort PV (4-8 ply max):\n- \n\n"
            "[BOT_MOVE]\nExplain:\n- \nNext-turn checklist:\n- \n"
        )
        out = parse_agent_report(fallback)
        out.raw_text = text
        return out
