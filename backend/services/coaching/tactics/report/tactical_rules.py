from __future__ import annotations

from ..schemas import CandidateFeatures, TacticalCandidate


SERIOUS_CP_LOSS = 100
SIGNIFICANT_MATERIAL_LOSS_CP = 300


def select_motif(candidate: TacticalCandidate,features: CandidateFeatures) -> tuple[str, str]:
    """Classify verified features into one tactical coaching motif."""
    defense = features.played_defense
    best = features.best_move
    pv = features.principal_variation

    if defense and defense.opponent_has_mate_in_one:
        return "defensive", "mate_threat"

    if (
        defense
        and defense.largest_immediate_capture_cp >= SIGNIFICANT_MATERIAL_LOSS_CP
    ):
        return "defensive", "hanging_piece"

    if best and best.gives_checkmate:
        return "offensive", "missed_check"

    if best and best.is_check:
        return "offensive", "missed_check"

    if best and best.is_capture:
        return "offensive", "missed_capture"

    if pv and pv.contains_checkmate:
        return "mixed", "mate_threat"

    if defense and defense.opponent_has_forcing_check:
        return "defensive", "king_safety"

    return "mixed", "calculation_error"


def confidence_for(
    candidate: TacticalCandidate,
    features: CandidateFeatures,
) -> str:
    """Determine confidence from directly verified evidence."""
    has_forced_mate = (
        candidate.mate_in_plies is not None
        or (
            features.best_move is not None
            and features.best_move.gives_checkmate
        )
        or (
            features.played_defense is not None
            and features.played_defense.opponent_has_mate_in_one
        )
    )

    has_large_material_loss = (
        features.played_defense is not None
        and features.played_defense.largest_immediate_capture_cp
        >= SIGNIFICANT_MATERIAL_LOSS_CP
    )

    if has_forced_mate or has_large_material_loss:
        return "high"

    if candidate.cp_loss >= SERIOUS_CP_LOSS:
        return "medium"

    return "low"