"""
HTTP client for the Lichess Opening Explorer API. Its only job is
"given a FEN, return real Explorer statistics or None" -- it contains no
classification/deviation logic and never raises on failure, matching this
codebase's existing graceful-degradation convention (e.g.
`PolyglotBook.open()` never crashing the app when data is unavailable).
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from ..config import OpeningDeviationSettings
from ..models.opening import ExplorerStats
from .models import ExplorerApiResponse, to_explorer_stats

logger = logging.getLogger(__name__)


class LichessExplorerClient:
    def __init__(self, settings: OpeningDeviationSettings):
        self._settings = settings

        headers = {"User-Agent": settings.explorer_user_agent}
        if settings.lichess_api_token:
            headers["Authorization"] = f"Bearer {settings.lichess_api_token}"

        self._client = httpx.AsyncClient(
            base_url=settings.explorer_base_url,
            timeout=settings.explorer_timeout_seconds,
            headers=headers,
        )

    async def fetch(self, fen: str) -> ExplorerStats | None:
        for attempt in range(self._settings.explorer_max_retries + 1):
            try:
                response = await self._client.get(
                    f"/{self._settings.explorer_dataset}",
                    params={"fen": fen},
                )

                if response.status_code == 429:
                    if attempt >= self._settings.explorer_max_retries:
                        break

                    delay = self._retry_delay(response, attempt)
                    logger.warning(
                        "Lichess Explorer rate-limited (attempt %d/%d), backing off %.1fs for fen=%s",
                        attempt + 1,
                        self._settings.explorer_max_retries,
                        delay,
                        fen,
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
            except httpx.HTTPError:
                logger.warning("Lichess Explorer request failed for fen=%s", fen, exc_info=True)
                return None

            try:
                raw = ExplorerApiResponse.model_validate(response.json())
            except ValueError:
                logger.warning("Lichess Explorer returned an unparseable response for fen=%s", fen)
                return None

            return to_explorer_stats(fen, raw)

        logger.warning(
            "Lichess Explorer still rate-limited after %d retries for fen=%s",
            self._settings.explorer_max_retries,
            fen,
        )
        return None

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")

        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass

        return self._settings.explorer_retry_backoff_seconds * (2**attempt)

    async def aclose(self) -> None:
        await self._client.aclose()
