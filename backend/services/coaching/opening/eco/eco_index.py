"""
ECO opening-name classification.

Openings are shallow (typically <=20 plies), so a flat dict keyed by a
canonical, space-joined UCI move-prefix gives O(1) lookup per ply and an
O(depth-of-game) "find the deepest match" walk -- the same asymptotic cost
as a trie, without custom traversal/serialization code. Revisit only if the
dataset grows large enough to matter, or a feature needs sibling/branch
enumeration (not needed here: `better_move`/`better_line` come from the
deviation engine, services/opening_deviation, not from this index).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ECO_INDEX_PATH = Path(__file__).parent / "data" / "eco_index.json"


@dataclass(frozen=True, slots=True)
class EcoEntry:
    eco: str
    name: str
    variation: str | None


class EcoIndex:
    """In-memory longest-move-prefix index for opening identification.

    Built once (e.g. during FastAPI lifespan startup) and shared across
    requests, mirroring how `services/stockfish.py` starts its engine pool
    once rather than per request.
    """

    def __init__(self, entries: dict[str, EcoEntry]):
        self._entries = entries

    def __len__(self) -> int:
        return len(self._entries)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_ECO_INDEX_PATH) -> EcoIndex:
        with open(path) as index_file:
            raw = json.load(index_file)

        entries = {
            prefix: EcoEntry(
                eco=data["eco"],
                name=data["name"],
                variation=data.get("variation"),
            )
            for prefix, data in raw.items()
            if not prefix.startswith("_")
        }
        return cls(entries)

    def identify(self, moves_uci: list[str]) -> tuple[EcoEntry | None, int]:
        """Return the deepest opening entry matched by a played-move prefix.

        Walks ply-by-ply and keeps the last (deepest) hit rather than
        stopping at the first match, so a more specific variation (e.g. the
        Najdorf) overrides a shallower generic entry (e.g. "Sicilian
        Defense") matched earlier in the same walk.
        """
        best: EcoEntry | None = None
        best_depth = 0
        prefix_parts: list[str] = []

        for depth, move_uci in enumerate(moves_uci, start=1):
            prefix_parts.append(move_uci)
            entry = self._entries.get(" ".join(prefix_parts))

            if entry is not None:
                best = entry
                best_depth = depth

        return best, best_depth
