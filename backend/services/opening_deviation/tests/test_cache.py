"""
SqliteOpeningCacheRepository tests against a real temp SQLite file: basic
get/put, persistence across a fresh connection, and LRU eviction at cap.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from services.opening_deviation.cache.repository import SqliteOpeningCacheRepository
from services.opening_deviation.models.opening import CandidateMove, ExplorerStats


def _stats(fen: str, total: int = 100) -> ExplorerStats:
    return ExplorerStats(
        fen=fen,
        eco="C50",
        opening_name="Italian Game",
        total_games=total,
        moves=[CandidateMove(uci="e2e4", san="e4", white=60, draws=30, black=10)],
    )


class SqliteOpeningCacheRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._db_path = str(Path(self._tmp.name) / "cache.sqlite3")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_miss_returns_none(self) -> None:
        repo = SqliteOpeningCacheRepository(self._db_path, max_size=10)
        self.assertIsNone(repo.get("nonexistent"))
        repo.close()

    def test_put_then_get_round_trips(self) -> None:
        repo = SqliteOpeningCacheRepository(self._db_path, max_size=10)
        stats = _stats("fen-a")

        repo.put("fen-a", stats)
        result = repo.get("fen-a")

        self.assertIsNotNone(result)
        self.assertEqual(result.eco, "C50")
        self.assertEqual(result.opening_name, "Italian Game")
        self.assertEqual(result.total_games, 100)
        self.assertEqual(len(result.moves), 1)
        self.assertEqual(result.moves[0].uci, "e2e4")
        repo.close()

    def test_put_overwrites_existing_key(self) -> None:
        repo = SqliteOpeningCacheRepository(self._db_path, max_size=10)

        repo.put("fen-a", _stats("fen-a", total=100))
        repo.put("fen-a", _stats("fen-a", total=500))

        self.assertEqual(len(repo), 1)
        self.assertEqual(repo.get("fen-a").total_games, 500)
        repo.close()

    def test_persists_across_connections(self) -> None:
        repo1 = SqliteOpeningCacheRepository(self._db_path, max_size=10)
        repo1.put("fen-a", _stats("fen-a"))
        repo1.close()

        repo2 = SqliteOpeningCacheRepository(self._db_path, max_size=10)
        self.assertEqual(repo2.get("fen-a").total_games, 100)
        repo2.close()

    def test_evicts_least_recently_accessed_when_over_capacity(self) -> None:
        repo = SqliteOpeningCacheRepository(self._db_path, max_size=2)

        repo.put("fen-a", _stats("fen-a"))
        repo.put("fen-b", _stats("fen-b"))
        # Touch fen-a so it's more recently used than fen-b.
        repo.get("fen-a")
        repo.put("fen-c", _stats("fen-c"))

        self.assertEqual(len(repo), 2)
        self.assertIsNone(repo.get("fen-b"))
        self.assertIsNotNone(repo.get("fen-a"))
        self.assertIsNotNone(repo.get("fen-c"))
        repo.close()

    def test_len_reflects_row_count(self) -> None:
        repo = SqliteOpeningCacheRepository(self._db_path, max_size=10)
        self.assertEqual(len(repo), 0)

        repo.put("fen-a", _stats("fen-a"))
        self.assertEqual(len(repo), 1)
        repo.close()


if __name__ == "__main__":
    unittest.main()
