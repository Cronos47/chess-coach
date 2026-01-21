import sys
import asyncio

# ✅ Windows: ensure asyncio supports subprocesses (needed by python-chess UCI engine)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    NewGameRequest,
    MoveRequest,
    UndoRequest,
    MoveResponse,
    StateResponse,
)
from .session import SESSION
from .analysis import update_mental_signals_after_move
from .agent import run_coach_agent
from . import chess_engine  # module import so ENGINE can be initialized safely


# ---------------- WebSocket manager ----------------

class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WSManager()

app = FastAPI(title="Agentic Chess Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Startup / Shutdown ----------------

@app.on_event("startup")
def startup():
    # ✅ Initialize Stockfish engine once (avoid import-time subprocess)
    if chess_engine.ENGINE is None:
        chess_engine.ENGINE = chess_engine.StockfishEngine()


@app.on_event("shutdown")
def shutdown():
    # Cleanup engine
    if chess_engine.ENGINE is not None:
        try:
            chess_engine.ENGINE.quit()
        except Exception:
            pass


# ---------------- REST endpoints ----------------

@app.post("/api/new_game", response_model=StateResponse)
def new_game(req: NewGameRequest):
    side = req.side.lower()
    if side not in ("white", "black"):
        raise HTTPException(status_code=400, detail="side must be 'white' or 'black'")

    difficulty = req.bot_difficulty.lower()
    if difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="bot_difficulty must be easy|medium|hard")

    verbosity = int(req.coach_verbosity)
    if verbosity < 1 or verbosity > 3:
        raise HTTPException(status_code=400, detail="coach_verbosity must be 1..3")

    SESSION.reset(side=side, difficulty=difficulty, verbosity=verbosity)

    # If player chose black, let bot play first (as white)
    if side == "black":
        if chess_engine.ENGINE is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        bot_move = chess_engine.ENGINE.get_bot_move(SESSION.board, SESSION.bot_difficulty)
        SESSION.board.push(bot_move)
        SESSION.move_list.append(bot_move.uci())

    state = SESSION.to_state()
    return StateResponse(state=state, agent_output=SESSION.last_agent_output)


@app.get("/api/state", response_model=StateResponse)
def get_state():
    # ✅ return last agent output so refresh restores tabs
    return StateResponse(state=SESSION.to_state(), agent_output=SESSION.last_agent_output)


@app.post("/api/undo", response_model=StateResponse)
def undo(req: UndoRequest):
    # allow undo only if at least one move exists
    if len(SESSION.move_list) == 0:
        return StateResponse(state=SESSION.to_state(), agent_output=SESSION.last_agent_output)

    # Undo one half-move (last move)
    SESSION.board.pop()
    SESSION.move_list.pop()

    # Count undo attempts (signal)
    SESSION.undo_attempts += 1

    # Keep last_agent_output (or you could clear it if you want)
    state = SESSION.to_state()
    return StateResponse(state=state, agent_output=SESSION.last_agent_output)


@app.post("/api/move", response_model=MoveResponse)
def make_move(req: MoveRequest):
    # Ensure engine exists
    if chess_engine.ENGINE is None:
        raise HTTPException(status_code=500, detail="Engine not initialized")

    # Apply self-report (optional)
    if req.self_report is not None:
        SESSION.self_report = req.self_report

    # Validate and play user's move
    uci = req.uci_move.strip()
    try:
        move = SESSION.board.parse_uci(uci)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UCI move")

    if move not in SESSION.board.legal_moves:
        raise HTTPException(status_code=400, detail="Illegal move")

    # Update think time
    if req.think_time_ms is not None:
        SESSION.think_times_ms.append(int(req.think_time_ms))

    # We compute mental streak updates after agent classification.
    # But we can compute "rapid after blunder" based on previous move state.
    # For now, update with move_quality=None (agent will compute later).
    SESSION.blunder_streak, SESSION.rapid_after_blunder = update_mental_signals_after_move(
        move_quality=None,
        think_time_ms=req.think_time_ms,
        last_move_was_blunder=(SESSION.blunder_streak > 0),
        current_blunder_streak=SESSION.blunder_streak,
    )

    # Push user move
    SESSION.board.push(move)
    SESSION.move_list.append(uci)

    # If game over after user's move, we can still run agent (optional),
    # but we will skip bot reply.
    bot_move_uci = None
    if not SESSION.board.is_game_over():
        bot_move = chess_engine.ENGINE.get_bot_move(SESSION.board, SESSION.bot_difficulty)
        SESSION.board.push(bot_move)
        bot_move_uci = bot_move.uci()
        SESSION.move_list.append(bot_move_uci)

    # Run agent after full ply (user + bot if any)
    agent_out = run_coach_agent(
        board=SESSION.board,
        move_list=SESSION.move_list,
        player_side=SESSION.player_side,
        bot_difficulty=SESSION.bot_difficulty,
        coach_verbosity=SESSION.coach_verbosity,
        signals={
            "think_times_ms": SESSION.think_times_ms,
            "blunder_streak": SESSION.blunder_streak,
            "undo_attempts": SESSION.undo_attempts,
            "rapid_after_blunder": SESSION.rapid_after_blunder,
            "self_report": SESSION.self_report,
        },
    )

    # Persist last agent output so refresh restores it
    SESSION.last_agent_output = agent_out

    state = SESSION.to_state()

    # WebSocket broadcast (optional enhancement)
    try:
        # fire-and-forget: safe in sync endpoint by running a loop task if possible
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                ws_manager.broadcast(
                    {"type": "update", "state": state.model_dump(), "agent_output": agent_out.model_dump()}
                )
            )
    except Exception:
        pass

    return MoveResponse(state=state, agent_output=agent_out, bot_move=bot_move_uci)


# ---------------- WebSocket ----------------

@app.websocket("/ws/game")
async def ws_game(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Send initial snapshot on connect
        await ws.send_json(
            {
                "type": "update",
                "state": SESSION.to_state().model_dump(),
                "agent_output": SESSION.last_agent_output.model_dump() if SESSION.last_agent_output else None,
            }
        )
        while True:
            # We don't require client messages; keep connection alive.
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)
