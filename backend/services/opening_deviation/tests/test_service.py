"""
OpeningDeviationService tests using a fake repository and a fake Explorer
client (dependency-injected, matching this codebase's established DI
testing pattern) -- no real network, no real SQLite.
"""

from __future__ import annotations

import unittest

from services.opening_deviation.config import OpeningDeviationSettings
from services.opening_deviation.deviation.service import OpeningDeviationService
from services.opening_deviation.models.opening import CandidateMove, ExplorerStats, MoveRecord

FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


class FakeRepository:
    def __init__(self) -> None:
        self.store: dict[str, ExplorerStats] = {}
        self.get_calls: list[str] = []
        self.put_calls: list[str] = []

    def get(self, key: str) -> ExplorerStats | None:
        self.get_calls.append(key)
        return self.store.get(key)

    def put(self, key: str, stats: ExplorerStats) -> None:
        self.put_calls.append(key)
        self.store[key] = stats

    def __len__(self) -> int:
        return len(self.store)

    def close(self) -> None:
        pass


class FakeExplorerClient:
    def __init__(self, responses: dict[str, ExplorerStats | None]) -> None:
        self._responses = responses
        self.fetch_calls: list[str] = []

    async def fetch(self, fen: str) -> ExplorerStats | None:
        self.fetch_calls.append(fen)
        return self._responses.get(fen)

    async def aclose(self) -> None:
        pass


def _stats(fen: str, mainline_uci: str = "e2e4") -> ExplorerStats:
    return ExplorerStats(
        fen=fen,
        total_games=1000,
        moves=[
            CandidateMove(uci=mainline_uci, white=600, draws=300, black=100),
            CandidateMove(uci="a2a3", white=1, draws=0, black=0),
        ],
    )


def _settings() -> OpeningDeviationSettings:
    return OpeningDeviationSettings(
        deviation_share_threshold=0.01, mainline_share_threshold=0.10, min_sample_games=50
    )


class OpeningDeviationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_stats_is_cache_first(self) -> None:
        repository = FakeRepository()
        cached = _stats(FEN_START)
        repository.store["rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"] = cached

        explorer_client = FakeExplorerClient({})
        service = OpeningDeviationService(repository, explorer_client, _settings())

        result = await service.get_stats(FEN_START)

        self.assertEqual(result, cached)
        self.assertEqual(explorer_client.fetch_calls, [])

    async def test_get_stats_fetches_and_persists_on_miss(self) -> None:
        repository = FakeRepository()
        fetched = _stats(FEN_START)
        explorer_client = FakeExplorerClient({FEN_START: fetched})
        service = OpeningDeviationService(repository, explorer_client, _settings())

        result = await service.get_stats(FEN_START)

        self.assertEqual(result, fetched)
        self.assertEqual(explorer_client.fetch_calls, [FEN_START])
        self.assertEqual(len(repository), 1)

    async def test_get_stats_does_not_cache_a_miss(self) -> None:
        repository = FakeRepository()
        explorer_client = FakeExplorerClient({})
        service = OpeningDeviationService(repository, explorer_client, _settings())

        result = await service.get_stats(FEN_START)

        self.assertIsNone(result)
        self.assertEqual(len(repository), 0)

    async def test_classify_move_mainline(self) -> None:
        repository = FakeRepository()
        explorer_client = FakeExplorerClient({FEN_START: _stats(FEN_START)})
        service = OpeningDeviationService(repository, explorer_client, _settings())

        result = await service.classify_move(FEN_START, "e2e4")

        self.assertEqual(result.classification, "MAINLINE")

    async def test_classify_move_deviation(self) -> None:
        repository = FakeRepository()
        explorer_client = FakeExplorerClient({FEN_START: _stats(FEN_START)})
        service = OpeningDeviationService(repository, explorer_client, _settings())

        result = await service.classify_move(FEN_START, "a2a3")

        self.assertEqual(result.classification, "DEVIATION")

    async def test_find_first_deviation_stops_at_first_deviation(self) -> None:
        repository = FakeRepository()
        explorer_client = FakeExplorerClient(
            {
                FEN_START: _stats(FEN_START),
                FEN_AFTER_E4: _stats(FEN_AFTER_E4),
            }
        )
        service = OpeningDeviationService(repository, explorer_client, _settings())

        records = [
            MoveRecord(position_fen=FEN_START, next_move="a2a3", ply=1),
            MoveRecord(position_fen=FEN_AFTER_E4, next_move="e2e4", ply=2),
        ]

        result = await service.find_first_deviation(records)

        self.assertTrue(result.found)
        self.assertEqual(result.ply, 1)
        self.assertEqual(result.played_move, "a2a3")
        # The second record must never have been looked at.
        self.assertEqual(explorer_client.fetch_calls, [FEN_START])

    async def test_find_first_deviation_returns_not_found_when_all_mainline(self) -> None:
        repository = FakeRepository()
        explorer_client = FakeExplorerClient(
            {
                FEN_START: _stats(FEN_START),
                FEN_AFTER_E4: _stats(FEN_AFTER_E4),
            }
        )
        service = OpeningDeviationService(repository, explorer_client, _settings())

        records = [
            MoveRecord(position_fen=FEN_START, next_move="e2e4", ply=1),
            MoveRecord(position_fen=FEN_AFTER_E4, next_move="e2e4", ply=2),
        ]

        result = await service.find_first_deviation(records)

        self.assertFalse(result.found)
        self.assertIsNone(result.ply)


if __name__ == "__main__":
    unittest.main()
