from __future__ import annotations

from ..schemas import AnnotatedMove, TacticalCandidate


SERIOUS_CP_LOSS = 100
TACTICAL_QUALITIES = frozenset({"mistake", "blunder"})


def select_candidates(valid_moves: list[AnnotatedMove]) -> list[TacticalCandidate]:
    """Select moves that warrant tactical feature extraction."""
    candidates: list[TacticalCandidate] = []

    for move in valid_moves:
        has_large_loss = move.cp_loss >= SERIOUS_CP_LOSS
        has_tactical_label = move.quality in TACTICAL_QUALITIES

        if not has_large_loss and not has_tactical_label:
            continue

        candidates.append(
            TacticalCandidate(
                ply=move.ply,
                move_number=move.move_number,
                player_color=move.color,
                fen_before=move.fen_before,
                played_san=move.played_san,
                played_uci=move.played_uci,
                best_move_san=move.best_move_san,
                best_move_uci=move.best_move_uci,
                principal_variation_uci=move.principal_variation_uci,
                cp_loss=move.cp_loss,
                quality=move.quality,
                mate_in_plies=move.mate_in_plies,
                depth=move.depth,
            )
        )

    return candidates
