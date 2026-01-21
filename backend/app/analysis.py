from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class MoveQuality:
    """
    Move quality label derived from evaluation swing (centipawns).
    """
    label: str
    swing_cp: Optional[int] = None


def classify_move_quality_from_swing(
    eval_before_cp: Optional[int],
    eval_after_cp: Optional[int],
) -> MoveQuality:
    """
    Classify a move using evaluation swing.

    Convention:
    - eval_before_cp and eval_after_cp are centipawn evaluations from the SAME POV.
      (For simplicity in this app, if you can't guarantee POV, treat them as "advantage for side to move"
       consistently based on your engine wrapper; otherwise pass None.)

    If either eval is None (mate/unknown), we default to "Good".

    Swing definition:
      swing = eval_after_cp - eval_before_cp
    We care about negative swings (position got worse for the player).

    Thresholds (simple, chess.com-like):
      >= -30   : Best/Good
      -31..-90 : Inaccuracy
      -91..-200: Mistake
      <= -201  : Blunder
    """
    if eval_before_cp is None or eval_after_cp is None:
        return MoveQuality(label="Good", swing_cp=None)

    swing = eval_after_cp - eval_before_cp  # negative is worse
    # Use absolute negative swing as "mistake magnitude"
    if swing >= -30:
        # If very small swing, call it Good; you can map exact 0 to Best if you want
        return MoveQuality(label="Good", swing_cp=swing)

    if -90 <= swing <= -31:
        return MoveQuality(label="Inaccuracy", swing_cp=swing)

    if -200 <= swing <= -91:
        return MoveQuality(label="Mistake", swing_cp=swing)

    return MoveQuality(label="Blunder", swing_cp=swing)


def update_mental_signals_after_move(
    *,
    move_quality: Optional[str],
    think_time_ms: Optional[int],
    last_move_was_blunder: bool,
    current_blunder_streak: int,
) -> Tuple[int, bool]:
    """
    Update mental-state signals based on the latest move.

    Inputs:
      move_quality: Best/Good/Inaccuracy/Mistake/Blunder or None (unknown yet)
      think_time_ms: time spent on this move (from UI), can be None
      last_move_was_blunder: whether previous player move was a blunder
      current_blunder_streak: current streak count prior to this move

    Returns:
      (new_blunder_streak, rapid_after_blunder)

    Rules (simple but useful):
    - If move_quality is Blunder or Mistake => increment streak (blunder streak counts "bad moves")
    - If move_quality is Good/Best/Inaccuracy => reset streak
    - rapid_after_blunder = True if last move was blunder and current think time is "very fast"
      (threshold: <= 1500ms), else False
    """
    rapid = False
    if last_move_was_blunder and think_time_ms is not None and think_time_ms <= 1500:
        rapid = True

    # If quality unknown, don't change streak (agent sets it later if you wire eval swing)
    if move_quality is None:
        return current_blunder_streak, rapid

    q = move_quality.strip()

    if q in ("Blunder", "Mistake"):
        return current_blunder_streak + 1, rapid

    if q in ("Good", "Best", "Inaccuracy"):
        return 0, rapid

    # Fallback: don't change
    return current_blunder_streak, rapid
