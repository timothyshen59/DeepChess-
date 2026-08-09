"""
Focused, isolated tests for routes/analyze.py -- a minimal FastAPI() app
with just this router (same pattern as
services/opening_deviation/tests/test_api.py), patching only
`routes.analyze.annotate_moves` (the real Stockfish boundary). PGN parsing
(`extract_moves`) runs for real -- it's pure, local, and not an external
dependency, so faking it would just be extra indirection for no benefit.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.analyze import router
from services.pgn_utils import extract_moves

PGN_FOUR_PLIES = "1. e4 e5 2. Nf3 Nc6 *"


def _annotate(moves: list[dict], cp_losses: list[float | None], quality: str = "good") -> dict:
    """Builds a fake `annotate_moves` return value shaped exactly like
    the real `_finalize_annotations` output, reusing the real move dicts
    `extract_moves` produced so every `MoveAnnotation` field is realistic."""
    annotated = [
        {
            **move,
            "cp_loss": cp_loss,
            "best_move_uci": None,
            "principal_variation": [],
            "quality": quality,
            "color_hex": "#000000",
        }
        for move, cp_loss in zip(moves, cp_losses)
    ]
    return {
        "moves": annotated,
        "failed_positions": 0,
        "total_positions": len(moves),
        "is_partial": False,
    }


class AnalyzeRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_normal_analysis_returns_well_formed_moves_and_averages(self) -> None:
        moves = extract_moves(PGN_FOUR_PLIES)
        fake_response = _annotate(moves, cp_losses=[0, 10, 20, 30])

        with patch("routes.analyze.annotate_moves", return_value=fake_response):
            response = self.client.post("/analyze", json={"pgn": PGN_FOUR_PLIES})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["moves"]), 4)
        self.assertEqual(body["moves"][0]["move_san"], "e4")
        self.assertEqual(body["total_positions"], 4)
        self.assertFalse(body["is_partial"])
        # Index parity: white = indices 0,2 -> cp_loss 0,20 -> avg 10.
        # black = indices 1,3 -> cp_loss 10,30 -> avg 20.
        self.assertEqual(body["avg_white_cp_loss"], 10)
        self.assertEqual(body["avg_black_cp_loss"], 20)

    def test_averages_are_computed_by_move_index_parity(self) -> None:
        moves = extract_moves(PGN_FOUR_PLIES)
        fake_response = _annotate(moves, cp_losses=[10, 20, 30, 40])

        with patch("routes.analyze.annotate_moves", return_value=fake_response):
            response = self.client.post("/analyze", json={"pgn": PGN_FOUR_PLIES})

        body = response.json()
        # indices 0,2 (white) -> 10,30 -> avg 20; indices 1,3 (black) -> 20,40 -> avg 30.
        self.assertEqual(body["avg_white_cp_loss"], 20)
        self.assertEqual(body["avg_black_cp_loss"], 30)

    def test_empty_move_list_returns_empty_analysis_without_crashing(self) -> None:
        # A PGN with no real movetext -- extract_moves returns [], and the
        # *real* annotate_moves([]) short-circuits before ever touching
        # Stockfish (verified directly in services/stockfish.py), so no
        # patch is needed here at all.
        response = self.client.post("/analyze", json={"pgn": "not a real pgn @@@"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["moves"], [])
        self.assertIsNone(body["avg_white_cp_loss"])
        self.assertIsNone(body["avg_black_cp_loss"])
        self.assertEqual(body["failed_positions"], 0)
        self.assertEqual(body["total_positions"], 0)
        self.assertFalse(body["is_partial"])

    def test_one_sided_color_data_when_one_color_has_no_scored_moves(self) -> None:
        # Only the white-side plies (indices 0, 2) have a real cp_loss;
        # both black-side plies came back None (e.g. a failed evaluation)
        # -- avg_black_cp_loss must be None, not a crash averaging an
        # empty list.
        moves = extract_moves(PGN_FOUR_PLIES)
        fake_response = _annotate(moves, cp_losses=[15, None, 25, None])

        with patch("routes.analyze.annotate_moves", return_value=fake_response):
            response = self.client.post("/analyze", json={"pgn": PGN_FOUR_PLIES})

        body = response.json()
        self.assertEqual(body["avg_white_cp_loss"], 20)
        self.assertIsNone(body["avg_black_cp_loss"])

    def test_invalid_pgn_returns_400(self) -> None:
        # An illegal move is what actually makes python-chess record a
        # parse error (same fixture pattern as
        # services/coaching/opening/tests/test_graph.py) -- real
        # extract_moves(), no patch needed, fails before ever reaching
        # annotate_moves.
        response = self.client.post("/analyze", json={"pgn": "1. e9 e5 *"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
