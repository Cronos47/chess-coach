from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ============================================================
# API REQUEST MODELS
# ============================================================

class NewGameRequest(BaseModel):
    side: str = Field(default="white", description="white or black")
    bot_difficulty: str = Field(default="medium", description="easy | medium | hard")
    coach_verbosity: int = Field(default=2, ge=1, le=3)


class MoveRequest(BaseModel):
    uci_move: str = Field(..., description="UCI move, e.g. e2e4")
    think_time_ms: Optional[int] = Field(
        default=None, description="Client-side think time for this move"
    )
    self_report: Optional[str] = Field(
        default=None, description="calm | tilted | tired | focused"
    )


class UndoRequest(BaseModel):
    pass


# ============================================================
# GAME STATE MODELS
# ============================================================

class ClockState(BaseModel):
    white_ms: int
    black_ms: int


class SignalState(BaseModel):
    think_times_ms: List[int] = []
    blunder_streak: int = 0
    undo_attempts: int = 0
    rapid_after_blunder: bool = False
    self_report: Optional[str] = None


class GameState(BaseModel):
    fen: str
    side_to_move: str
    move_list: List[str]
    captured_pieces: Dict[str, List[str]]
    clocks: ClockState
    signals: SignalState
    game_over: bool = False
    result: Optional[str] = None


# ============================================================
# AGENT OUTPUT MODELS
# ============================================================

class CoachOutput(BaseModel):
    move_quality: str
    bullets: List[str]
    pv: Optional[str] = None


class MentalOutput(BaseModel):
    observed_signals: List[str]
    inference: str
    micro_reset_tip: str


class PositionOutput(BaseModel):
    eval: str
    why: List[str]
    threats: List[str]
    plans: Dict[str, List[str]]


class AgentOutput(BaseModel):
    coach: CoachOutput
    mental: MentalOutput
    position: PositionOutput
    raw_text: Optional[str] = None


# ============================================================
# API RESPONSE MODELS
# ============================================================

class MoveResponse(BaseModel):
    state: GameState
    agent_output: Optional[AgentOutput] = None
    bot_move: Optional[str] = None


class StateResponse(BaseModel):
    state: GameState
    agent_output: Optional[AgentOutput] = None


class ErrorResponse(BaseModel):
    error: str
