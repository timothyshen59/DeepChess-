"""
Offline BFS crawl from the starting position, populating the cache
repository with real Lichess Explorer statistics ahead of request time.
Not part of request-time runtime -- run on demand:

    python -m services.opening_deviation.warmup.builder

Branches below `warmup_min_frequency_to_expand` are pruned, and expansion
stops past `warmup_max_ply`. `warmup_target_position_count` is a soft
stop: once reached, no new branches are enqueued, but already-queued work
finishes so the tree isn't truncated unevenly mid-branch.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

import chess

from ..cache.repository import SqliteOpeningCacheRepository
from ..config import OpeningDeviationSettings, settings as default_settings
from ..explorer.client import LichessExplorerClient
from ..models.opening import canonical_fen_key

logger = logging.getLogger(__name__)


class WarmupBuilder:
    def __init__(
        self,
        repository: SqliteOpeningCacheRepository,
        explorer_client: LichessExplorerClient,
        settings: OpeningDeviationSettings,
    ):
        self._repository = repository
        self._explorer_client = explorer_client
        self._settings = settings

    async def run(self) -> None:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(chess.STARTING_FEN, 0)])
        target_reached = False

        while queue:
            fen, ply = queue.popleft()
            key = canonical_fen_key(fen)

            if key in visited:
                continue
            visited.add(key)

            stats = await self._explorer_client.fetch(fen)
            await asyncio.sleep(self._settings.warmup_request_delay_seconds)

            if stats is None:
                continue

            self._repository.put(key, stats)

            if not target_reached and len(self._repository) >= self._settings.warmup_target_position_count:
                logger.info("Warmup target position count reached; no further branches will be enqueued.")
                target_reached = True

            if target_reached or ply >= self._settings.warmup_max_ply or stats.total_games <= 0:
                continue

            self._enqueue_children(fen, ply, stats, queue)

        logger.info("Warmup complete. Cached %d positions.", len(self._repository))

    def _enqueue_children(self, fen: str, ply: int, stats, queue: deque[tuple[str, int]]) -> None:
        board = chess.Board(fen)

        for move in stats.moves:
            share = move.total_games / stats.total_games

            if share < self._settings.warmup_min_frequency_to_expand:
                continue

            try:
                chess_move = chess.Move.from_uci(move.uci)
            except ValueError:
                continue

            if chess_move not in board.legal_moves:
                continue

            child_board = board.copy(stack=False)
            child_board.push(chess_move)
            queue.append((child_board.fen(), ply + 1))


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)

    repository = SqliteOpeningCacheRepository(
        db_path=default_settings.cache_db_path,
        max_size=default_settings.cache_max_size,
    )
    explorer_client = LichessExplorerClient(default_settings)
    builder = WarmupBuilder(repository, explorer_client, default_settings)

    try:
        await builder.run()
    finally:
        await explorer_client.aclose()
        repository.close()


if __name__ == "__main__":
    asyncio.run(_main())
