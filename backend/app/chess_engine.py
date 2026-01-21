import chess
import chess.engine
from typing import Dict, Any

from .config import find_stockfish_binary


class StockfishEngine:
    """
    Thin wrapper around python-chess UCI engine.

    Used for BOTH:
    - bot move selection
    - engine-grounded analysis (eval, PV, multipv)
    """

    def __init__(self):
        engine_path = find_stockfish_binary()
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

        # Default depths by difficulty
        self.depth_by_level = {
            "easy": 6,
            "medium": 10,
            "hard": 15,
        }

    def get_bot_move(self, board: chess.Board, difficulty: str) -> chess.Move:
        depth = self.depth_by_level.get(difficulty, 10)
        limit = chess.engine.Limit(depth=depth)
        result = self.engine.play(board, limit)
        return result.move

    def analyze_position(
        self,
        board: chess.Board,
        depth: int = 12,
        multipv: int = 1,
    ) -> Dict[str, Any]:
        limit = chess.engine.Limit(depth=depth)
        info = self.engine.analyse(board, limit, multipv=multipv)

        def parse_info(entry):
            score = entry["score"].pov(board.turn)
            if score.is_mate():
                eval_str = f"mate {score.mate()}"
                eval_cp = None
            else:
                eval_cp = score.score()
                eval_str = f"{eval_cp} cp"

            pv_moves = []
            if "pv" in entry:
                pv_moves = [m.uci() for m in entry["pv"][:8]]

            return {
                "eval_str": eval_str,
                "eval_cp": eval_cp,
                "pv": pv_moves,
            }

        if isinstance(info, list):
            parsed = [parse_info(e) for e in info]
            return {
                "primary": parsed[0],
                "multipv": parsed,
            }

        parsed = parse_info(info)
        return {
            "primary": parsed,
            "multipv": [parsed],
        }

    def quit(self):
        try:
            self.engine.quit()
        except Exception:
            pass


# Global engine instance (single-user app)
ENGINE: StockfishEngine | None = None

