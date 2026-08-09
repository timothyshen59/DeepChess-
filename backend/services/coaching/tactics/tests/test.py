from __future__ import annotations

import unittest
import pprint
from services.coaching.tactics.graph import build_tactics_graph
from services.coaching.tactics.schemas import AnnotatedMove


class TacticsGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = build_tactics_graph()

    def test_detects_defensive_hanging_queen(self) -> None:
        annotated_move = AnnotatedMove(
            ply=1,
            move_number=1,
            color="white",
            quality="blunder",
            cp_loss=900,
            fen_before="4k3/8/8/8/8/3q4/4Q3/4K3 w - - 0 1",
            played_san="Qe3",
            played_uci="e2e3",
            best_move_san="Qxd3",
            best_move_uci="e2d3",
            principal_variation_uci=["e2d3"],
            depth=18,
        )

        result = self.graph.invoke({"annotated_moves": [annotated_move]})

        print("\n\n========== GRAPH RESULT ==========")
        pprint.pprint(result)
        print("========== END GRAPH RESULT ==========\n")

        report = result["report"]

        self.assertEqual(len(report.input_issues), 0)
        self.assertEqual(len(report.crucial_mistakes), 1)

        lesson = report.crucial_mistakes[0]
        self.assertEqual(lesson.category, "defensive")
        self.assertEqual(lesson.motif, "hanging_piece")
        self.assertIn("immediate capture", lesson.explanation)

    def test_illegal_played_move_is_reported_without_crashing(self) -> None:
        annotated_move = AnnotatedMove(
            ply=1,
            move_number=1,
            color="white",
            quality="blunder",
            cp_loss=400,
            fen_before="4k3/8/8/8/8/8/3qQ3/4K3 w - - 0 1",
            played_san="Qh9",
            played_uci="e2h9",
            best_move_san="Qxd2",
            best_move_uci="e2d2",
        )

        result = self.graph.invoke({"annotated_moves": [annotated_move]})
        report = result["report"]

        self.assertEqual(len(report.crucial_mistakes), 0)
        self.assertEqual(len(report.input_issues), 1)
        self.assertEqual(report.input_issues[0].code, "illegal_played_move")


if __name__ == "__main__":
    unittest.main()
