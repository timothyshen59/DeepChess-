"""
A fake `OpeningDeviationService` covering exactly the Najdorf line used by
`najdorf_deviation.pgn`: mainline through White's 7th move, then the
deviation reply 7...h6 (theory's top choice is 7...Be7), then a
continuation for the resulting "better line". Shared between
`services/coaching/opening/tests/test_graph.py` and
`tests/e2e/test_coaching_pipeline.py` so the two suites don't each
hand-roll the same canned data.

FENs are computed by replaying the SAN lines with python-chess rather than
hand-transcribed, the same spirit as the old `build_fixture_book.py`.
"""

from __future__ import annotations

import chess

from services.opening_deviation.models.opening import (
    CandidateMove,
    ClassificationResult,
    canonical_fen_key,
)

MAINLINE_SAN = [
    "e4",
    "c5",
    "Nf3",
    "d6",
    "d4",
    "cxd4",
    "Nxd4",
    "Nf6",
    "Nc3",
    "a6",
    "Be2",
    "e5",
    "Nb3",
]
BETTER_CONTINUATION_SAN = ["O-O", "O-O", "Be3", "Nc6"]


class FakeDeviationService:
    """Duck-typed stand-in for `OpeningDeviationService` -- same
    dependency-injection testing pattern as
    `services/opening_deviation/tests/test_service.py`'s fakes, one layer
    up. Unmapped positions default to OUT_OF_BOOK, matching a real
    "no Explorer data available" scenario.
    """

    _OUT_OF_BOOK = ClassificationResult(classification="OUT_OF_BOOK", total_games=0)

    def __init__(
        self,
        classify_responses: dict[str, ClassificationResult] | None = None,
        best_candidates: dict[str, CandidateMove] | None = None,
    ):
        self._classify_responses = classify_responses or {}
        self._best_candidates = best_candidates or {}

    async def classify_move(self, fen: str, next_move: str) -> ClassificationResult:
        return self._classify_responses.get(canonical_fen_key(fen), self._OUT_OF_BOOK)

    async def best_candidate(self, fen: str) -> CandidateMove | None:
        return self._best_candidates.get(canonical_fen_key(fen))


def _mainline_result(move: chess.Move, san: str) -> ClassificationResult:
    candidate = CandidateMove(uci=move.uci(), san=san, white=600, draws=300, black=100)
    return ClassificationResult(
        classification="MAINLINE",
        played_move_share=0.9,
        total_games=1000,
        candidate_moves=[candidate],
        best_move=candidate,
    )


def build_najdorf_fake_service() -> FakeDeviationService:
    classify_responses: dict[str, ClassificationResult] = {}
    board = chess.Board()

    for san in MAINLINE_SAN:
        fen_before = canonical_fen_key(board.fen())
        move = board.push_san(san)
        classify_responses[fen_before] = _mainline_result(move, san)

    # Deviation point: 7...h6 was played; theory's top choice is 7...Be7.
    deviation_fen = canonical_fen_key(board.fen())
    be7 = board.parse_san("Be7")
    be7_candidate = CandidateMove(uci=be7.uci(), san="Be7", white=850, draws=100, black=50)
    classify_responses[deviation_fen] = ClassificationResult(
        classification="DEVIATION",
        played_move_share=0.01,
        total_games=1000,
        candidate_moves=[be7_candidate],
        best_move=be7_candidate,
    )

    # The better line's continuation past the deviation, for
    # `best_candidate` lookups used to extend it.
    best_candidates: dict[str, CandidateMove] = {}
    board.push(be7)

    for san in BETTER_CONTINUATION_SAN:
        fen_before = canonical_fen_key(board.fen())
        move = board.parse_san(san)
        best_candidates[fen_before] = CandidateMove(
            uci=move.uci(), san=san, white=600, draws=300, black=100
        )
        board.push(move)

    return FakeDeviationService(classify_responses, best_candidates)
