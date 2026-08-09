"""
Process-lifetime singletons for the opening deviation engine: the cache
repository and the Explorer HTTP client are constructed once at FastAPI
lifespan startup (mirrors `services/coaching/opening/opening_deps.py`'s
lifecycle), not per request.
"""

from __future__ import annotations

import logging

from .cache.repository import OpeningCacheRepository, SqliteOpeningCacheRepository
from .config import OpeningDeviationSettings
from .config import settings as default_settings
from .deviation.service import OpeningDeviationService
from .explorer.client import LichessExplorerClient

logger = logging.getLogger(__name__)

_SERVICE: OpeningDeviationService | None = None
_REPOSITORY: OpeningCacheRepository | None = None
_EXPLORER_CLIENT: LichessExplorerClient | None = None


def load_deps(settings: OpeningDeviationSettings = default_settings) -> None:
    """Call once during FastAPI lifespan startup."""
    global _SERVICE, _REPOSITORY, _EXPLORER_CLIENT

    if _SERVICE is not None:
        return

    _REPOSITORY = SqliteOpeningCacheRepository(
        db_path=settings.cache_db_path,
        max_size=settings.cache_max_size,
    )
    _EXPLORER_CLIENT = LichessExplorerClient(settings)
    _SERVICE = OpeningDeviationService(_REPOSITORY, _EXPLORER_CLIENT, settings)

    logger.info(
        "Opening deviation engine ready. cached_positions=%d dataset=%s",
        len(_REPOSITORY),
        settings.explorer_dataset,
    )


async def close_deps() -> None:
    """Call once during FastAPI shutdown."""
    global _SERVICE, _REPOSITORY, _EXPLORER_CLIENT

    if _EXPLORER_CLIENT is not None:
        await _EXPLORER_CLIENT.aclose()

    if _REPOSITORY is not None:
        _REPOSITORY.close()

    _SERVICE = None
    _REPOSITORY = None
    _EXPLORER_CLIENT = None


def get_service() -> OpeningDeviationService:
    if _SERVICE is None:
        raise RuntimeError("Opening deviation engine dependencies have not been loaded.")

    return _SERVICE
