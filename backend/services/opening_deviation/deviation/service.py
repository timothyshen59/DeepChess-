"""
Orchestrates the cache repository, the Explorer client, and the classifier.
Neither the repository nor the classifier knows the other exists -- this is
the only file that does.
"""

from __future__ import annotations

from ..cache.repository import OpeningCacheRepository
from ..config import OpeningDeviationSettings
from ..explorer.client import LichessExplorerClient
from ..models.opening import (
    CandidateMove,
    ClassificationResult,
    DeviationResult,
    ExplorerStats,
    MoveRecord,
    canonical_fen_key,
)
from .classifier import best_candidate_move, classify


class OpeningDeviationService:
    def __init__(
        self,
        repository: OpeningCacheRepository,
        explorer_client: LichessExplorerClient,
        settings: OpeningDeviationSettings,
    ):
        self._repository = repository
        self._explorer_client = explorer_client
        self._settings = settings

    async def get_stats(self, fen: str) -> ExplorerStats | None:
        """Cache-first lookup. On a miss, queries the Explorer API and
        persists the result (keyed by the canonical, transposition-aware
        FEN) before returning it."""
        key = canonical_fen_key(fen)
        cached = self._repository.get(key)

        if cached is not None:
            return cached

        fetched = await self._explorer_client.fetch(fen)

        if fetched is not None:
            self._repository.put(key, fetched)

        return fetched

    async def classify_move(self, fen: str, next_move: str) -> ClassificationResult:
        stats = await self.get_stats(fen)
        return classify(next_move, stats, self._settings)

    async def best_candidate(self, fen: str) -> CandidateMove | None:
        """The most-played move at a position, independent of anything a
        player actually played there. Used to extend a deviation into a
        multi-move "better line" continuation."""
        stats = await self.get_stats(fen)
        return best_candidate_move(stats.moves) if stats else None

    async def find_first_deviation(self, records: list[MoveRecord]) -> DeviationResult:
        """Walks records in ply order; stops and returns immediately on
        the first DEVIATION. Records after that point are never
        processed, matching the existing Polyglot-book pipeline's
        first-deviation-only behavior."""
        for record in records:
            result = await self.classify_move(record.position_fen, record.next_move)

            if result.classification == "DEVIATION":
                return DeviationResult(
                    found=True,
                    ply=record.ply,
                    position_fen=record.position_fen,
                    played_move=record.next_move,
                    classification=result,
                )

        return DeviationResult(found=False)
