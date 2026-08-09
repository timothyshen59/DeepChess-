from __future__ import annotations

from ..schemas import CandidateFeatures, TacticalCandidate, TacticalLesson
from .tactical_rules import (
    SIGNIFICANT_MATERIAL_LOSS_CP,
    confidence_for,
    select_motif,
)


def _lesson_explanation(candidate: TacticalCandidate, features: CandidateFeatures) -> tuple[str, str]:
    defense = features.played_defense
    best = features.best_move
    pv = features.principal_variation

    played = candidate.played_san or candidate.played_uci
    better = candidate.best_move_san or candidate.best_move_uci

    if defense and defense.opponent_has_mate_in_one:
        return (
            f"{played} allowed an immediate mating move. Before committing to "
            "a move, you must verify whether the opponent has a forcing checkmate.",
            "After every candidate move, scan every opponent check first; "
            "reject the move if any check is mate.",
        )

    if defense and defense.immediate_capture_targets:
        target = defense.immediate_capture_targets[0]

        return (
            f"{played} left your {target.piece} on {target.square} available "
            f"to an immediate capture. The tactical error is defensive: the "
            f"move did not preserve the piece's safety."
            + (f" {better} avoids that concession." if better else ""),
            "Before moving, ask: what can my opponent capture immediately "
            "after this move?",
        )

    if best and best.gives_checkmate:
        return (
            f"{played} missed a mating move: {better}. The winning idea was "
            "to prioritize forcing checks.",
            "Use checks-captures-threats order whenever the enemy king has "
            "limited escape squares.",
        )

    if best and best.is_check:
        return (
            f"{played} missed the forcing check {better}. Checks constrain "
            "the reply set and should be calculated before quiet moves.",
            "For each position, list all legal checks and calculate the "
            "opponent's forced responses.",
        )

    if best and best.is_capture:
        return (
            f"{played} missed the tactical capture {better}. The best line "
            "wins material or removes a key defender.",
            "Before playing a quiet move, compare all forcing captures for "
            "both sides.",
        )

    if defense and defense.opponent_has_forcing_check:
        return (
            f"{played} weakened king safety and gave the opponent a forcing "
            "checking continuation.",
            "After choosing a move, explicitly test every legal opponent "
            "check before finalizing it.",
        )

    material_detail = ""
    if pv and pv.material_swing_cp >= SIGNIFICANT_MATERIAL_LOSS_CP:
        material_detail = " The engine line also shows a significant material swing."

    return (
        f"{played} was a tactical calculation error."
        + (f" {better} was the stronger continuation." if better else "")
        + material_detail,
        "Use a final blunder check: opponent checks, captures, threats, "
        "then your forcing replies.",
    )


def build_lesson(candidate: TacticalCandidate, features: CandidateFeatures) -> TacticalLesson:
    """Build a deterministic coaching lesson from verified features."""
    category, motif = select_motif(candidate, features)
    explanation, habit = _lesson_explanation(candidate, features)

    return TacticalLesson(
        ply=candidate.ply,
        move_number=candidate.move_number,
        player_color=candidate.player_color,
        category=category,
        motif=motif,
        played_move=candidate.played_san or candidate.played_uci,
        better_move=candidate.best_move_san or candidate.best_move_uci,
        cp_loss=candidate.cp_loss,
        explanation=explanation,
        calculation_habit=habit,
        confidence=confidence_for(candidate, features),
    )