"""
Model/example games, looked up by ECO code.

A plain function over one bundled dataset -- not a Protocol/repository
class. There is exactly one implementation and one dataset today; promote
this to a formal interface only if a second source (e.g. a live game
database/API) is actually planned. Per the architecture plan, the
production dataset should be generated OFFLINE from a master-game PGN
corpus, classified via eco/eco_index.py -- this module only loads the
resulting index, it doesn't build it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..schemas import ModelGameRef

DEFAULT_MODEL_GAMES_PATH = Path(__file__).parent / "data" / "model_games_index.json"


@lru_cache(maxsize=1)
def _load_index(path: str) -> dict[str, list[ModelGameRef]]:
    with open(path) as index_file:
        raw = json.load(index_file)

    return {
        eco: [ModelGameRef(**game) for game in games]
        for eco, games in raw.items()
        if not eco.startswith("_")
    }


def get_model_games(
    eco: str | None,
    path: Path | str = DEFAULT_MODEL_GAMES_PATH,
) -> list[ModelGameRef]:
    """Return curated model games for an ECO code, or [] if none are known."""
    if not eco:
        return []

    return _load_index(str(path)).get(eco, [])
