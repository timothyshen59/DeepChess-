"""
FastAPI TestClient tests against routes/opening_deviation.py, with the
opening-deviation deps module patched to a fake service so no real
network/cache is touched. Verifies the HTTP boundary only -- business
logic is already covered by test_service.py/test_classifier.py.
"""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.opening_deviation import router
from services.opening_deviation import deps
from services.opening_deviation.models.opening import (
    CandidateMove,
    ClassificationResult,
    DeviationResult,
    ExplorerStats,
)


class FakeService:
    def __init__(self) -> None:
        self.stats_by_fen: dict[str, ExplorerStats] = {}
        self.classify_result = ClassificationResult(
            classification="MAINLINE", total_games=100, played_move_share=0.9
        )
        self.deviation_result = DeviationResult(found=False)

    async def get_stats(self, fen: str) -> ExplorerStats | None:
        return self.stats_by_fen.get(fen)

    async def classify_move(self, fen: str, next_move: str) -> ClassificationResult:
        return self.classify_result

    async def find_first_deviation(self, records) -> DeviationResult:
        return self.deviation_result


class OpeningDeviationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_service = FakeService()
        deps._SERVICE = self.fake_service  # noqa: SLF001 -- test-only override, restored in tearDown

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        deps._SERVICE = None  # noqa: SLF001

    def test_get_stats_returns_404_when_no_data(self) -> None:
        response = self.client.get("/opening-deviation/stats", params={"fen": "unknown-fen"})
        self.assertEqual(response.status_code, 404)

    def test_get_stats_returns_data_when_available(self) -> None:
        fen = "some-fen"
        self.fake_service.stats_by_fen[fen] = ExplorerStats(
            fen=fen,
            total_games=1000,
            moves=[CandidateMove(uci="e2e4", san="e4", white=600, draws=300, black=100)],
        )

        response = self.client.get("/opening-deviation/stats", params={"fen": fen})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_games"], 1000)
        self.assertEqual(body["moves"][0]["uci"], "e2e4")

    def test_classify_move(self) -> None:
        response = self.client.post(
            "/opening-deviation/classify",
            json={"position_fen": "fen", "next_move": "e2e4"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["classification"], "MAINLINE")

    def test_find_deviation(self) -> None:
        self.fake_service.deviation_result = DeviationResult(
            found=True, ply=3, position_fen="fen", played_move="a2a3"
        )

        response = self.client.post(
            "/opening-deviation/find-deviation",
            json={"records": [{"position_fen": "fen", "next_move": "a2a3", "ply": 3}]},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["found"])
        self.assertEqual(body["ply"], 3)


if __name__ == "__main__":
    unittest.main()
