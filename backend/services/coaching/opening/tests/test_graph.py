"""
Unit tests for the opening agent's graph, using fakes for the ECO index and
the deviation engine (see `graph.py`: `build_opening_graph(deps)` takes
both as parameters precisely so tests don't need a real dataset file, a
live Lichess Explorer call, or a running Stockfish pool for the parts that
don't need one).

`evaluate_mistakes` does call the real `services.stockfish.aannotate_moves`,
so these tests start/stop a real Stockfish pool -- mirroring
tactics/tests/test.py's use of the compiled graph directly, just async.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from services.coaching.opening.eco.eco_index import EcoEntry, EcoIndex
from services.coaching.opening.graph import OpeningDeps, build_opening_graph
from services.coaching.opening.tests.fixtures.najdorf_fake_service import (
    FakeDeviationService,
    build_najdorf_fake_service,
)
from services.stockfish import start_stockfish_pool, stop_stockfish_pool

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_PGN_PATH = FIXTURES_DIR / "najdorf_deviation.pgn"

NAJDORF_MOVES_UCI = [
    "e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6",
]


def _fake_eco_index() -> EcoIndex:
    """A tiny in-memory index -- no dataset file touched."""
    prefix = " ".join(NAJDORF_MOVES_UCI)
    return EcoIndex({prefix: EcoEntry(eco="B90", name="Sicilian Defense", variation="Najdorf Variation")})


def _empty_eco_index() -> EcoIndex:
    return EcoIndex({})


class OpeningGraphTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        start_stockfish_pool()

    @classmethod
    def tearDownClass(cls) -> None:
        stop_stockfish_pool()

    async def test_identifies_opening_and_flags_deviation_with_real_book(self) -> None:
        pgn = FIXTURE_PGN_PATH.read_text()
        deps = OpeningDeps(
            eco_index=_fake_eco_index(),
            deviation_service=build_najdorf_fake_service(),
            theory_max_plies=20,
        )
        graph = build_opening_graph(deps)

        result = await graph.ainvoke({"pgn": pgn, "fen": None, "user_color": None})
        report = result["report"]

        self.assertEqual(report.opening.eco, "B90")
        self.assertEqual(report.opening.variation, "Najdorf Variation")

        self.assertEqual(report.deviation.status, "deviated")
        self.assertEqual(report.deviation.move_number, 7)
        self.assertEqual(report.deviation.player_color, "black")
        self.assertEqual(report.deviation.played_san, "h6")
        self.assertEqual(report.deviation.theory_tier, "DEVIATION")
        self.assertEqual(report.deviation.better_move_san, "Be7")
        # Coverage continues a few plies past the deviation.
        self.assertEqual(
            report.deviation.better_line_san[:4],
            ["Be7", "O-O", "O-O", "Be3"],
        )

    async def test_reports_book_unavailable_when_no_book_is_configured(self) -> None:
        pgn = FIXTURE_PGN_PATH.read_text()
        deps = OpeningDeps(
            eco_index=_fake_eco_index(),
            deviation_service=FakeDeviationService(),
            theory_max_plies=20,
        )
        graph = build_opening_graph(deps)

        result = await graph.ainvoke({"pgn": pgn, "fen": None, "user_color": None})
        report = result["report"]

        self.assertEqual(report.deviation.status, "book_unavailable")
        self.assertEqual(report.deviation.ply, None)

    async def test_malformed_pgn_reports_an_invalid_pgn_issue(self) -> None:
        deps = OpeningDeps(
            eco_index=_empty_eco_index(),
            deviation_service=FakeDeviationService(),
            theory_max_plies=20,
        )
        graph = build_opening_graph(deps)

        # An illegal move (e9 isn't a legal pawn move) is what actually
        # makes python-chess record a parse error -- unlike arbitrary
        # gibberish text, which it parses as a valid, empty game instead.
        result = await graph.ainvoke({"pgn": "1. e9 e5 *", "fen": None, "user_color": None})
        report = result["report"]

        self.assertEqual(report.opening.eco, None)
        self.assertEqual(len(report.input_issues), 1)
        self.assertEqual(report.input_issues[0].code, "invalid_pgn")

    async def test_pgn_with_no_moves_reports_a_no_moves_issue(self) -> None:
        deps = OpeningDeps(
            eco_index=_empty_eco_index(),
            deviation_service=FakeDeviationService(),
            theory_max_plies=20,
        )
        graph = build_opening_graph(deps)

        # python-chess's PGN parser is lenient: text with no real movetext
        # parses as a valid, empty game rather than raising.
        result = await graph.ainvoke({"pgn": "not a real pgn @@@", "fen": None, "user_color": None})
        report = result["report"]

        self.assertEqual(report.opening.eco, None)
        self.assertEqual(len(report.input_issues), 1)
        self.assertEqual(report.input_issues[0].code, "no_moves")

    async def test_evaluate_mistakes_flags_a_real_inaccuracy(self) -> None:
        pgn = FIXTURE_PGN_PATH.read_text()
        deps = OpeningDeps(
            eco_index=_fake_eco_index(),
            deviation_service=build_najdorf_fake_service(),
            theory_max_plies=20,
        )
        graph = build_opening_graph(deps)

        result = await graph.ainvoke({"pgn": pgn, "fen": None, "user_color": None})
        report = result["report"]
        # Whatever Stockfish flags, it should be a real, well-formed note --
        # not asserting a specific ply since engine opinions can shift with
        # search depth/version.
        for mistake in report.critical_mistakes:
            self.assertGreater(mistake.cp_loss, 0)
            self.assertIn(mistake.severity, {"mistake", "blunder"})


if __name__ == "__main__":
    unittest.main()
