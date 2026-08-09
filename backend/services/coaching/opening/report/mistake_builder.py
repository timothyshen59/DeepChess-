from __future__ import annotations

from ..schemas import CriticalMistake, MistakeSeverity


def build_critical_mistake(
    move: dict,
    quality: MistakeSeverity,
    cp_loss: int,
    best_move_san: str | None,
) -> CriticalMistake:
    """Build a deterministic, rule-based critical-mistake note.

    No LLM in v1 (see architecture plan decision #1) -- same rule-based
    approach as tactics/report/lesson_builder.py, just simpler: opening
    mistakes are reported purely from Stockfish cp-loss, not motif-classified,
    since the heavier tactical-feature pipeline (move_feature/defensive_feature)
    isn't needed to flag "this opening move was objectively bad."
    """
    played = move["move_san"]
    ply = move["move_number"]

    headline = (
        f"{played} was a serious opening blunder"
        if quality == "blunder"
        else f"{played} was an inaccurate opening move"
    )

    explanation = headline
    if best_move_san:
        explanation += f"; {best_move_san} kept a much stronger position"
    explanation += f" (lost about {cp_loss} centipawns of evaluation)."

    return CriticalMistake(
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=move["color"],
        played_san=played,
        best_move_san=best_move_san,
        cp_loss=cp_loss,
        severity=quality,
        explanation=explanation,
    )
