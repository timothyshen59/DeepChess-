"""
WarmupBuilder tests using a fake Explorer client returning canned
responses keyed by FEN, and a real (temp-file) SqliteOpeningCacheRepository
-- deterministic BFS/pruning/dedup, no real network.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import chess

from services.opening_deviation.cache.repository import SqliteOpeningCacheRepository
from services.opening_deviation.config import OpeningDeviationSettings
from services.opening_deviation.models.opening import (
    CandidateMove,
    ExplorerStats,
    canonical_fen_key,
)
from services.opening_deviation.warmup.builder import WarmupBuilder

START = chess.STARTING_FEN


def _board_after(*ucis: str) -> chess.Board:
    board = chess.Board()
    for uci in ucis:
        board.push(chess.Move.from_uci(uci))
    return board


class FakeExplorerClient:
    def __init__(self, responses: dict[str, ExplorerStats]) -> None:
        self._responses = {canonical_fen_key(fen): stats for fen, stats in responses.items()}
        self.fetch_calls: list[str] = []

    async def fetch(self, fen: str) -> ExplorerStats | None:
        self.fetch_calls.append(fen)
        return self._responses.get(canonical_fen_key(fen))


def _settings(**overrides) -> OpeningDeviationSettings:
    # warmup_request_delay_seconds=0 by default -- these tests talk to a
    # fake, in-memory client and don't need real pacing; the one test
    # that verifies pacing itself overrides this explicitly.
    defaults = dict(
        warmup_max_ply=30,
        warmup_min_frequency_to_expand=0.10,
        warmup_target_position_count=100_000,
        warmup_request_delay_seconds=0,
    )
    defaults.update(overrides)
    return OpeningDeviationSettings(**defaults)


class WarmupBuilderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._db_path = str(Path(self._tmp.name) / "cache.sqlite3")
        self._repository = SqliteOpeningCacheRepository(self._db_path, max_size=1000)

    def tearDown(self) -> None:
        self._repository.close()
        self._tmp.cleanup()

    async def test_caches_the_starting_position(self) -> None:
        stats = ExplorerStats(fen=START, total_games=1000, moves=[])
        explorer_client = FakeExplorerClient({START: stats})
        builder = WarmupBuilder(self._repository, explorer_client, _settings())

        await builder.run()

        self.assertIsNotNone(self._repository.get(canonical_fen_key(START)))

    async def test_expands_only_moves_above_the_frequency_floor(self) -> None:
        after_e4 = _board_after("e2e4").fen()
        after_a3 = _board_after("a2a3").fen()

        responses = {
            START: ExplorerStats(
                fen=START,
                total_games=1000,
                moves=[
                    CandidateMove(uci="e2e4", white=600, draws=300, black=90),  # 99% -- expand
                    CandidateMove(uci="a2a3", white=5, draws=3, black=2),  # 1% -- prune
                ],
            ),
            after_e4: ExplorerStats(fen=after_e4, total_games=10, moves=[]),
            after_a3: ExplorerStats(fen=after_a3, total_games=10, moves=[]),
        }
        explorer_client = FakeExplorerClient(responses)
        builder = WarmupBuilder(
            self._repository, explorer_client, _settings(warmup_min_frequency_to_expand=0.10)
        )

        await builder.run()

        self.assertIsNotNone(self._repository.get(canonical_fen_key(after_e4)))
        self.assertIsNone(self._repository.get(canonical_fen_key(after_a3)))

    async def test_does_not_expand_past_max_ply(self) -> None:
        after_e4 = _board_after("e2e4").fen()

        responses = {
            START: ExplorerStats(
                fen=START,
                total_games=1000,
                moves=[CandidateMove(uci="e2e4", white=600, draws=300, black=100)],
            ),
            after_e4: ExplorerStats(
                fen=after_e4,
                total_games=1000,
                moves=[CandidateMove(uci="e7e5", white=600, draws=300, black=100)],
            ),
        }
        explorer_client = FakeExplorerClient(responses)
        builder = WarmupBuilder(self._repository, explorer_client, _settings(warmup_max_ply=0))

        await builder.run()

        self.assertIsNotNone(self._repository.get(canonical_fen_key(START)))
        self.assertIsNone(self._repository.get(canonical_fen_key(after_e4)))
        # Only the root position should ever have been queried.
        self.assertEqual(len(explorer_client.fetch_calls), 1)

    async def test_does_not_revisit_transposed_positions(self) -> None:
        # 1. Nf3 Nf6 2. c4 and 1. c4 Nf6 2. Nf3 transpose to the same
        # position -- the crawl must only fetch it once.
        via_nf3_first = _board_after("g1f3", "g8f6", "c2c4").fen()
        via_c4_first = _board_after("c2c4", "g8f6", "g1f3").fen()
        self.assertEqual(canonical_fen_key(via_nf3_first), canonical_fen_key(via_c4_first))

        after_nf3 = _board_after("g1f3").fen()
        after_nf3_nf6 = _board_after("g1f3", "g8f6").fen()
        after_c4 = _board_after("c2c4").fen()
        after_c4_nf6 = _board_after("c2c4", "g8f6").fen()

        responses = {
            START: ExplorerStats(
                fen=START,
                total_games=1000,
                moves=[
                    CandidateMove(uci="g1f3", white=500, draws=300, black=100),
                    CandidateMove(uci="c2c4", white=60, draws=30, black=10),
                ],
            ),
            after_nf3: ExplorerStats(
                fen=after_nf3,
                total_games=900,
                moves=[CandidateMove(uci="g8f6", white=500, draws=300, black=100)],
            ),
            after_nf3_nf6: ExplorerStats(
                fen=after_nf3_nf6,
                total_games=900,
                moves=[CandidateMove(uci="c2c4", white=500, draws=300, black=100)],
            ),
            after_c4: ExplorerStats(
                fen=after_c4,
                total_games=100,
                moves=[CandidateMove(uci="g8f6", white=60, draws=30, black=10)],
            ),
            after_c4_nf6: ExplorerStats(
                fen=after_c4_nf6,
                total_games=100,
                moves=[CandidateMove(uci="g1f3", white=60, draws=30, black=10)],
            ),
            via_nf3_first: ExplorerStats(fen=via_nf3_first, total_games=50, moves=[]),
        }
        explorer_client = FakeExplorerClient(responses)
        builder = WarmupBuilder(
            self._repository, explorer_client, _settings(warmup_min_frequency_to_expand=0.0)
        )

        await builder.run()

        transposed_key = canonical_fen_key(via_nf3_first)
        fetch_count = sum(
            1 for fen in explorer_client.fetch_calls if canonical_fen_key(fen) == transposed_key
        )
        self.assertEqual(fetch_count, 1)

    async def test_paces_requests_with_the_configured_delay(self) -> None:
        """Concurrency was already 1; the crawl having no throttling at
        all was the actual cause of getting rate-limited. Patches
        asyncio.sleep to a no-op so the test itself doesn't wait."""
        stats = ExplorerStats(fen=START, total_games=1000, moves=[])
        explorer_client = FakeExplorerClient({START: stats})
        builder = WarmupBuilder(
            self._repository, explorer_client, _settings(warmup_request_delay_seconds=1.5)
        )

        with patch("services.opening_deviation.warmup.builder.asyncio.sleep") as mock_sleep:
            await builder.run()

        mock_sleep.assert_awaited_once_with(1.5)


if __name__ == "__main__":
    unittest.main()
