"""
Persistent, offline-usable key -> ExplorerStats storage. No chess or
classification logic lives here -- the key is just an opaque string to this
layer; canonicalizing a FEN into that key is the service layer's job.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Protocol

from ..models.opening import CandidateMove, ExplorerStats


class OpeningCacheRepository(Protocol):
    def get(self, key: str) -> ExplorerStats | None: ...
    def put(self, key: str, stats: ExplorerStats) -> None: ...
    def __len__(self) -> int: ...
    def close(self) -> None: ...


class SqliteOpeningCacheRepository:
    """SQLite-backed cache (stdlib, no new dependency), size-capped with
    least-recently-used eviction so it can grow unattended during a warmup
    crawl without needing external infra."""

    def __init__(self, db_path: str, max_size: int):
        self._max_size = max_size
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opening_positions (
                canonical_fen TEXT PRIMARY KEY,
                eco TEXT,
                opening_name TEXT,
                total_games INTEGER NOT NULL,
                moves_json TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                last_accessed REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, key: str) -> ExplorerStats | None:
        row = self._conn.execute(
            "SELECT eco, opening_name, total_games, moves_json "
            "FROM opening_positions WHERE canonical_fen = ?",
            (key,),
        ).fetchone()

        if row is None:
            return None

        self._conn.execute(
            "UPDATE opening_positions SET last_accessed = ? WHERE canonical_fen = ?",
            (time.time(), key),
        )
        self._conn.commit()

        eco, opening_name, total_games, moves_json = row
        moves = [CandidateMove(**move) for move in json.loads(moves_json)]

        return ExplorerStats(
            fen=key,
            eco=eco,
            opening_name=opening_name,
            total_games=total_games,
            moves=moves,
        )

    def put(self, key: str, stats: ExplorerStats) -> None:
        now = time.time()
        moves_json = json.dumps([move.model_dump() for move in stats.moves])

        self._conn.execute(
            """
            INSERT INTO opening_positions
                (canonical_fen, eco, opening_name, total_games, moves_json, fetched_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(canonical_fen) DO UPDATE SET
                eco=excluded.eco,
                opening_name=excluded.opening_name,
                total_games=excluded.total_games,
                moves_json=excluded.moves_json,
                fetched_at=excluded.fetched_at,
                last_accessed=excluded.last_accessed
            """,
            (key, stats.eco, stats.opening_name, stats.total_games, moves_json, now, now),
        )
        self._conn.commit()
        self._evict_if_over_capacity()

    def _evict_if_over_capacity(self) -> None:
        overflow = len(self) - self._max_size

        if overflow <= 0:
            return

        self._conn.execute(
            """
            DELETE FROM opening_positions WHERE canonical_fen IN (
                SELECT canonical_fen FROM opening_positions
                ORDER BY last_accessed ASC
                LIMIT ?
            )
            """,
            (overflow,),
        )
        self._conn.commit()

    def __len__(self) -> int:
        (count,) = self._conn.execute("SELECT COUNT(*) FROM opening_positions").fetchone()
        return count

    def close(self) -> None:
        self._conn.close()
