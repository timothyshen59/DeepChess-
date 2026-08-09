"""
Integration test: exercises the real Stockfish adapter, not a mock.

    pytest -m integration
      -> real /analyze request through the real router
      -> real services.stockfish.annotate_moves
      -> a real Stockfish subprocess pool
      -> real chess analysis

`routes/tests/test_analyze.py` already covers the route's business logic
(averaging, index parity, empty/one-sided data) with `annotate_moves`
faked -- this file deliberately does not re-assert any of that (see "do
not duplicate tests unnecessarily between levels"). It only proves the
real engine adapter actually works end to end: a real process starts,
receives real positions, and returns a well-formed result.

Requires a real `stockfish` binary on `STOCKFISH_PATH` (or the default
lookup in services/stockfish.py). Not run by default -- `pytest -m integration`.
"""

from __future__ import annotations

import unittest

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.analyze import router
from services.stockfish import start_stockfish_pool, stop_stockfish_pool

PGN_WITH_A_REAL_BLUNDER = "1. e4 e5 2. Bc4 Nf6 3. Qh5 *"


@pytest.mark.integration
class AnalyzeStockfishIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        start_stockfish_pool()

    @classmethod
    def tearDownClass(cls) -> None:
        stop_stockfish_pool()

    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_analyze_request_produces_a_valid_result_via_real_stockfish(self) -> None:
        response = self.client.post("/analyze", json={"pgn": PGN_WITH_A_REAL_BLUNDER})

        self.assertEqual(response.status_code, 200)
        body = response.json()

        # Real engine communication happened: every ply got a real
        # evaluation, not a stub -- exactly what the unit-tier fakes can't
        # prove by construction.
        self.assertEqual(len(body["moves"]), 5)
        self.assertEqual(body["total_positions"], 5)
        self.assertEqual(body["failed_positions"], 0)
        self.assertFalse(body["is_partial"])

        for move in body["moves"]:
            self.assertIn(
                move["quality"],
                {"brilliant", "good", "inaccuracy", "mistake", "blunder", "unknown"},
            )
            self.assertIsInstance(move["principal_variation"], list)


if __name__ == "__main__":
    unittest.main()
