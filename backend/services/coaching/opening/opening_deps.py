"""
Process-lifetime singletons for the opening agent: the ECO index is loaded
once (mirrors `services/stockfish.py`'s engine-pool lifecycle) and the
compiled graph is built once, not per request. The deviation engine itself
is a shared singleton owned by `services/opening_deviation/deps.py` --
this module only borrows a reference to it, it does not open or close it.
"""

from __future__ import annotations

import logging

from config import settings
from services.opening_deviation import deps as opening_deviation_deps

from .eco.eco_index import EcoIndex
from .graph import OpeningDeps, build_opening_graph

logger = logging.getLogger(__name__)

_DEPS: OpeningDeps | None = None
_GRAPH = None


def load_deps() -> None:
    """Call once during FastAPI lifespan startup, after
    `opening_deviation_deps.load_deps()` has already run."""
    global _DEPS, _GRAPH

    if _DEPS is not None:
        return

    eco_index = (
        EcoIndex.load(settings.eco_index_path)
        if settings.eco_index_path
        else EcoIndex.load()  # falls back to the bundled seed dataset
    )

    _DEPS = OpeningDeps(
        eco_index=eco_index,
        deviation_service=opening_deviation_deps.get_service(),
        theory_max_plies=settings.opening_theory_max_plies,
    )
    _GRAPH = build_opening_graph(_DEPS)

    logger.info("Opening agent ready. eco_entries=%s", len(eco_index))


def close_deps() -> None:
    """Call once during FastAPI shutdown, before
    `opening_deviation_deps.close_deps()` tears down the shared service."""
    global _DEPS, _GRAPH

    _DEPS = None
    _GRAPH = None


def get_deps() -> OpeningDeps:
    if _DEPS is None:
        raise RuntimeError("Opening agent dependencies have not been loaded.")

    return _DEPS


def get_graph():
    if _GRAPH is None:
        raise RuntimeError("Opening agent graph has not been built.")

    return _GRAPH
