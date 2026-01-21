from dataclasses import dataclass, field
from typing import List, Dict, Optional

import chess

from .models import GameState, ClockState, SignalState, AgentOutput


def _empty_captured() -> Dict[str, List[str]]:
    return {"white": [], "black": []}


@dataclass
class Session:
    board: chess.Board = field(default_factory=chess.Board)
    player_side: str = "white"  # "white" or "black"
    bot_difficulty: str = "medium"
    coach_verbosity: int = 2

    move_list: List[str] = field(default_factory=list)  # UCI moves (string)
    captured_pieces: Dict[str, List[str]] = field(default_factory=_empty_captured)

    # Simple clocks
    white_ms: int = 5 * 60 * 1000
    black_ms: int = 5 * 60 * 1000

    # Mental signals
    think_times_ms: List[int] = field(default_factory=list)
    blunder_streak: int = 0
    undo_attempts: int = 0
    rapid_after_blunder: bool = False
    self_report: Optional[str] = None

    # ✅ Persist last agent output across refresh
    last_agent_output: Optional[AgentOutput] = None

    def reset(self, side: str, difficulty: str, verbosity: int):
        self.board = chess.Board()
        self.player_side = side
        self.bot_difficulty = difficulty
        self.coach_verbosity = verbosity
        self.move_list = []
        self.captured_pieces = _empty_captured()
        self.white_ms = 5 * 60 * 1000
        self.black_ms = 5 * 60 * 1000
        self.think_times_ms = []
        self.blunder_streak = 0
        self.undo_attempts = 0
        self.rapid_after_blunder = False
        self.self_report = None
        self.last_agent_output = None

    def to_state(self) -> GameState:
        clocks = ClockState(white_ms=self.white_ms, black_ms=self.black_ms)
        signals = SignalState(
            think_times_ms=self.think_times_ms,
            blunder_streak=self.blunder_streak,
            undo_attempts=self.undo_attempts,
            rapid_after_blunder=self.rapid_after_blunder,
            self_report=self.self_report,
        )

        # Determine whose turn (from board.turn)
        side_to_move = "white" if self.board.turn == chess.WHITE else "black"

        # Game over / result
        game_over = self.board.is_game_over()
        result = self.board.result() if game_over else None

        return GameState(
            fen=self.board.fen(),
            side_to_move=side_to_move,
            move_list=self.move_list,
            captured_pieces=self.captured_pieces,
            clocks=clocks,
            signals=signals,
            game_over=game_over,
            result=result,
        )


# Single-user in-memory session
SESSION = Session()
