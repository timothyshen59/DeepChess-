from __future__ import annotations

import chess

from .analysis.board_state import safe_board
from .analysis.defensive_features import defensive_feature
from .analysis.move_features import move_feature
from .analysis.pv_inspection import inspect_pv
from .pipeline.candidate_selection import select_candidates
from .report.lesson_builder import build_lesson
from .report.report_builder import build_report
from .schemas import CandidateFeatures, TacticalCandidate, TacticalLesson
from .state import TacticsState
from .pipeline.validation import validate_moves

from .strategic.engine import StrategicExplanationEngine
from .strategic.models import BoardDelta, StrategicFact
from .strategic.registry import default_strategic_detectors


def _build_best_move_delta(
    candidate: TacticalCandidate,
) -> BoardDelta | None:
    if candidate.best_move_uci is None:
        return None

    if candidate.best_move_uci == candidate.played_uci:
        return None

    board_before = chess.Board(candidate.fen_before)
    best_move = chess.Move.from_uci(candidate.best_move_uci)

    if best_move not in board_before.legal_moves:
        raise ValueError(
            f"Candidate ply={candidate.ply} has illegal best move {candidate.best_move_uci}"
        )

    board_after = board_before.copy(stack=False)
    board_after.push(best_move)

    return BoardDelta.from_boards(
        board_before=board_before,
        board_after=board_after,
        best_move=best_move,
    )


def validate_annotated_moves(state: TacticsState) -> dict:
    """Validate raw annotations before tactical feature extraction."""
    valid_moves, issues = validate_moves(state.get("annotated_moves", []))

    return {
        "valid_moves": valid_moves,
        "input_issues": issues,
    }


def select_tactical_candidates(state: TacticsState) -> dict:
    """Select tactical candidates from validated move annotations."""
    candidates = select_candidates(state.get("valid_moves", []))

    return {
        "candidates": candidates,
        "feature_updates": {},
    }


def compute_best_move_features(state: TacticsState) -> dict:
    """Compute best-move facts in one parallel graph branch."""
    updates: dict[int, CandidateFeatures] = {}

    for candidate in state.get("candidates", []):
        board = safe_board(candidate.fen_before)

        if board is None:
            continue

        updates[candidate.ply] = CandidateFeatures(
            best_move=move_feature(
                board=board,
                move_uci=candidate.best_move_uci,
            )
        )

    return {"feature_updates": updates}


def compute_played_move_features(state: TacticsState) -> dict:
    """Compute played-move and defensive facts in one parallel branch."""
    updates: dict[int, CandidateFeatures] = {}

    for candidate in state.get("candidates", []):
        board = safe_board(candidate.fen_before)

        if board is None:
            continue

        updates[candidate.ply] = CandidateFeatures(
            played_move=move_feature(
                board=board,
                move_uci=candidate.played_uci,
            ),
            played_defense=defensive_feature(
                board_before=board,
                played_uci=candidate.played_uci,
            ),
        )

    return {"feature_updates": updates}


def compute_pv_features(state: TacticsState) -> dict:
    """Compute principal-variation facts in one parallel branch."""
    updates: dict[int, CandidateFeatures] = {}

    for candidate in state.get("candidates", []):
        board = safe_board(candidate.fen_before)

        if board is None:
            continue

        updates[candidate.ply] = CandidateFeatures(
            principal_variation=inspect_pv(
                board_before=board,
                pv_uci=candidate.principal_variation_uci,
            )
        )

    return {"feature_updates": updates}


def assemble_tactics_report(state: TacticsState) -> dict:
    """Build at most four ranked tactical lessons from merged features."""
    features_by_ply = state.get("feature_updates", {})

    ranked_candidates = sorted(
        state.get("candidates", []),
        key=lambda candidate: candidate.cp_loss,
        reverse=True,
    )

    lessons: list[TacticalLesson] = []

    for candidate in ranked_candidates:
        if len(lessons) == 4:
            break

        features = features_by_ply.get(candidate.ply)

        if features is None:
            continue

        lessons.append(
            build_lesson(
                candidate=candidate,
                features=features,
            )
        )

    return {
        "report": build_report(
            lessons=lessons,
            input_issues=state.get("input_issues", []),
        )
    }


def strategic_explanations(
    state: TacticsState,
) -> dict[str, dict[int, tuple[StrategicFact, ...]]]:
    report = state["report"]

    candidates_by_move = {
        (
            candidate.move_number,
            candidate.player_color,
        ): candidate
        for candidate in state.get("candidates", [])
    }

    engine = StrategicExplanationEngine(detectors=default_strategic_detectors())

    facts_by_ply: dict[int, tuple[StrategicFact, ...]] = {}

    for lesson in report.crucial_mistakes:
        candidate = candidates_by_move.get(
            (
                lesson.move_number,
                lesson.player_color,
            )
        )

        if candidate is None:
            continue

        delta = _build_best_move_delta(candidate)

        if delta is None:
            continue

        explanation = engine.explain(delta)

        top_facts = explanation.facts[:3]

        if top_facts:
            facts_by_ply[candidate.ply] = top_facts

    return {
        "strategic_facts_by_ply": facts_by_ply,
    }
