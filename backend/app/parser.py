import re
from typing import Optional, Dict, Any, List


SECTION_HEADERS = {
    "mental": "1) Mental State Check",
    "position": "2) Position Snapshot",
    "move_quality": "3) Move Quality",
    "coaching": "4) Coaching",
    "bot": "5) Bot Move",
}


def _extract_section(text: str, start_header: str, end_headers: List[str]) -> Optional[str]:
    """
    Extract text between start_header and the nearest of end_headers.
    """
    start_idx = text.find(start_header)
    if start_idx == -1:
        return None

    start_idx += len(start_header)
    end_idx = len(text)
    for h in end_headers:
        idx = text.find(h, start_idx)
        if idx != -1:
            end_idx = min(end_idx, idx)

    return text[start_idx:end_idx].strip()


def parse_agent_report_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse the agent's strict-format text into structured JSON
    for the three UI tabs.

    Returns None if parsing fails (frontend can show raw text).
    """
    try:
        mental_raw = _extract_section(
            text,
            SECTION_HEADERS["mental"],
            [SECTION_HEADERS["position"]],
        )
        position_raw = _extract_section(
            text,
            SECTION_HEADERS["position"],
            [SECTION_HEADERS["move_quality"]],
        )
        coaching_raw = _extract_section(
            text,
            SECTION_HEADERS["coaching"],
            [SECTION_HEADERS["bot"]],
        )

        if not (mental_raw and position_raw and coaching_raw):
            return None

        # --- Mental ---
        mental = {
            "observed_signals": _extract_bullets(mental_raw, "Observed signals"),
            "inference": _extract_line(mental_raw, "Inference"),
            "micro_reset_tip": _extract_line(mental_raw, "10-second micro-reset"),
        }

        # --- Position ---
        position = {
            "eval": _extract_line(position_raw, "Eval"),
            "why": _extract_bullets(position_raw, "Why"),
            "threats": _extract_bullets(position_raw, "Immediate threats"),
            "plans": {
                "white": _extract_bullets(position_raw, "Plans (White)"),
                "black": _extract_bullets(position_raw, "Plans (Black)"),
            },
        }

        # --- Coaching ---
        coach = {
            "move_quality": _extract_line(text, "Label"),
            "bullets": _extract_bullets(coaching_raw, "Actionable"),
            "pv": _extract_line(coaching_raw, "Short PV"),
        }

        return {
            "mental": mental,
            "position": position,
            "coach": coach,
        }
    except Exception:
        return None


# ----------------------------
# Small parsing helpers
# ----------------------------

def _extract_line(block: str, label: str) -> str:
    """
    Extract a single-line value after 'label:'.
    """
    pattern = rf"{label}\s*:\s*(.+)"
    match = re.search(pattern, block)
    return match.group(1).strip() if match else ""


def _extract_bullets(block: str, label: str) -> List[str]:
    """
    Extract bullet points under a given label.
    """
    start = block.find(label)
    if start == -1:
        return []

    lines = block[start:].splitlines()[1:]
    bullets = []
    for line in lines:
        line = line.strip()
        if line.startswith("-"):
            bullets.append(line.lstrip("-").strip())
        else:
            break
    return bullets
