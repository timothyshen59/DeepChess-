"""
Pure unit tests for classify() -- hand-built ExplorerStats fixtures, no
network, no cache. Covers all four classifications, including the
explicit "thin sample must not become DEVIATION" invariant.
"""

from __future__ import annotations

import unittest

from services.opening_deviation.config import OpeningDeviationSettings
from services.opening_deviation.deviation.classifier import classify
from services.opening_deviation.models.opening import CandidateMove, ExplorerStats

FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"


def _settings(**overrides) -> OpeningDeviationSettings:
    defaults = dict(
        deviation_share_threshold=0.01, mainline_share_threshold=0.10, min_sample_games=50
    )
    defaults.update(overrides)
    return OpeningDeviationSettings(**defaults)


def _stats(moves: list[CandidateMove]) -> ExplorerStats:
    total = sum(move.total_games for move in moves)
    return ExplorerStats(fen=FEN, total_games=total, moves=moves)


class ClassifierTests(unittest.TestCase):
    def test_mainline_move(self) -> None:
        # 900/1000 share -- clearly mainline.
        stats = _stats(
            [
                CandidateMove(uci="e2e4", white=500, draws=200, black=200),
                CandidateMove(uci="d2d4", white=60, draws=20, black=20),
            ]
        )

        result = classify("e2e4", stats, _settings())

        self.assertEqual(result.classification, "MAINLINE")
        self.assertAlmostEqual(result.played_move_share, 900 / 1000)

    def test_sideline_move(self) -> None:
        # 80/1000 share (8%) -- above the 1% deviation floor, below the
        # 10% mainline bar.
        stats = _stats(
            [
                CandidateMove(uci="g1f3", white=500, draws=300, black=120),
                CandidateMove(uci="b1c3", white=40, draws=30, black=10),
            ]
        )

        result = classify("b1c3", stats, _settings())

        self.assertEqual(result.classification, "SIDELINE")

    def test_rare_move_is_a_deviation(self) -> None:
        # 1/1000 share (0.1%) -- clearly below the 1% floor.
        stats = _stats(
            [
                CandidateMove(uci="g1f3", white=600, draws=300, black=99),
                CandidateMove(uci="b1a3", white=1, draws=0, black=0),
            ]
        )

        result = classify("b1a3", stats, _settings())

        self.assertEqual(result.classification, "DEVIATION")
        self.assertAlmostEqual(result.played_move_share, 1 / 1000)
        self.assertEqual(result.best_move.uci, "g1f3")

    def test_move_absent_entirely_is_a_deviation(self) -> None:
        stats = _stats([CandidateMove(uci="c7c5", white=50, draws=30, black=20)])

        result = classify("e2e4", stats, _settings())

        self.assertEqual(result.classification, "DEVIATION")
        self.assertEqual(result.played_move_share, 0.0)

    def test_thin_sample_is_out_of_book_not_a_false_deviation(self) -> None:
        # Only 3 total recorded games -- far below min_sample_games. Must
        # not confidently call this a deviation just because the raw
        # percentage looks low.
        stats = _stats(
            [
                CandidateMove(uci="g1f3", white=2, draws=0, black=0),
                CandidateMove(uci="b1a3", white=1, draws=0, black=0),
            ]
        )

        result = classify("b1a3", stats, _settings())

        self.assertEqual(result.classification, "OUT_OF_BOOK")
        self.assertIsNone(result.played_move_share)

    def test_no_stats_at_all_is_out_of_book(self) -> None:
        result = classify("e2e4", None, _settings())

        self.assertEqual(result.classification, "OUT_OF_BOOK")
        self.assertEqual(result.total_games, 0)
        self.assertIsNone(result.best_move)

    def test_configurable_thresholds_are_respected(self) -> None:
        # 8% share: SIDELINE under defaults, DEVIATION under a stricter
        # 10% deviation floor.
        stats = _stats(
            [
                CandidateMove(uci="g1f3", white=600, draws=270, black=50),
                CandidateMove(uci="b1c3", white=50, draws=20, black=10),
            ]
        )

        default_result = classify("b1c3", stats, _settings())
        self.assertEqual(default_result.classification, "SIDELINE")

        strict_result = classify(
            "b1c3", stats, _settings(deviation_share_threshold=0.10, mainline_share_threshold=0.50)
        )
        self.assertEqual(strict_result.classification, "DEVIATION")


if __name__ == "__main__":
    unittest.main()
