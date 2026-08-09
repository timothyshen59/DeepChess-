"""
Pure classification: given a played move and the Explorer statistics at
that position, decide MAINLINE / SIDELINE / DEVIATION / OUT_OF_BOOK. No
HTTP, no cache access -- this is the same frequency-tier reasoning already
implemented and unit-tested this session for the Polyglot-book pipeline
(`services/coaching/opening/analysis/deviation.py::_classify_tier`), ported
to this module's vocabulary.

OUT_OF_BOOK is returned whenever there isn't enough evidence to confidently
call a move a real deviation -- a thin sample must never be silently
upgraded into DEVIATION just because a raw percentage happens to look low.
"""

from __future__ import annotations

from ..config import OpeningDeviationSettings
from ..models.opening import CandidateMove, Classification, ClassificationResult, ExplorerStats


def classify(
    next_move: str,
    stats: ExplorerStats | None,
    settings: OpeningDeviationSettings,
) -> ClassificationResult:
    if stats is None or stats.total_games < settings.min_sample_games:
        return ClassificationResult(
            classification="OUT_OF_BOOK",
            total_games=stats.total_games if stats else 0,
            candidate_moves=stats.moves if stats else [],
            best_move=best_candidate_move(stats.moves) if stats else None,
        )

    played_share = _played_share(next_move, stats)
    classification: Classification

    if played_share >= settings.mainline_share_threshold:
        classification = "MAINLINE"
    elif played_share >= settings.deviation_share_threshold:
        classification = "SIDELINE"
    else:
        classification = "DEVIATION"

    return ClassificationResult(
        classification=classification,
        played_move_share=played_share,
        total_games=stats.total_games,
        candidate_moves=stats.moves,
        best_move=best_candidate_move(stats.moves),
    )


def _played_share(next_move: str, stats: ExplorerStats) -> float:
    if stats.total_games <= 0:
        return 0.0

    played = next((move for move in stats.moves if move.uci == next_move), None)

    if played is None:
        return 0.0

    return played.total_games / stats.total_games


def best_candidate_move(moves: list[CandidateMove]) -> CandidateMove | None:
    """The most-played candidate move in a list of Explorer candidates.
    Shared with `OpeningDeviationService.best_candidate` so "what's the
    best move here" has one implementation, not two."""
    return max(moves, key=lambda move: move.total_games, default=None)
