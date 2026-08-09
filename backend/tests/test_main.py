"""
Integration test for the real application composition: `main.py`'s actual
`app`/`lifespan`, booted via `TestClient`, with no hand-constructed
`OpeningDeps` and no bypassing `opening_deps.py`/`services/opening_deviation/deps.py`.

Every other test in this repo either constructs `OpeningDeps` by hand
(the opening/coordinator graph unit tests) or builds its own fixture-backed
deps directly (the e2e suite) -- none of them boot `main.py` itself, so
none of them protect the one thing that's genuinely wiring-shaped: that
`opening_deviation_deps.load_deps()` runs *before* `opening_deps.load_deps()`
(the latter calls `opening_deviation_deps.get_service()`, which raises if
the former hasn't run yet -- see `services/coaching/opening/opening_deps.py`).

Fakes only the two real external boundaries: a real Stockfish subprocess
pool, and a real network call to Lichess. Settings, `EcoIndex.load()`, and
both `deps.py` modules' real DI wiring all run unfaked.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import DEFAULT, AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from services.coaching.opening import opening_deps
from services.opening_deviation import deps as opening_deviation_deps


async def _fake_aannotate_moves(moves: list[dict]) -> dict:
    """Stands in for a real Stockfish batch (same technique as
    services/coaching/opening/tests/test_graph.py). Every ply comes back
    "good" -- this test only cares that the route completes correctly
    through the real DI graph, not what Stockfish would have found."""
    return {
        "moves": [{"quality": "good", "cp_loss": 0, "best_move_uci": None} for _ in moves],
        "failed_positions": 0,
        "total_positions": len(moves),
        "is_partial": False,
    }


def _record_call_and_pass_through(call_order: list[str], name: str):
    """`side_effect` for a `wraps=`-patched mock: records that this
    function was called, then returns `DEFAULT` so `wraps` still invokes
    the real underlying function -- the real `load_deps()` genuinely
    runs, we just also observe when."""

    def _side_effect(*args, **kwargs):
        call_order.append(name)
        return DEFAULT

    return _side_effect


class AppBootstrapTests(unittest.TestCase):
    def test_boots_and_serves_a_real_route_with_deps_loaded_in_order(self) -> None:
        call_order: list[str] = []

        # The real dev cache (services/opening_deviation/data/opening_cache.sqlite3)
        # has thousands of real rows from manual testing this session --
        # get_stats() checks the cache *before* calling fetch(), so without
        # this override the route would serve real cached data and never
        # even reach the patched fetch() below. Point at an isolated,
        # guaranteed-empty path instead -- no global mutable test state.
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        isolated_cache_path = str(Path(tmp_dir.name) / "test_cache.sqlite3")

        with (
            patch("main.start_stockfish_pool"),
            patch("main.stop_stockfish_pool"),
            patch.object(
                opening_deviation_deps.default_settings, "cache_db_path", isolated_cache_path
            ),
            patch(
                "services.opening_deviation.explorer.client.LichessExplorerClient.fetch",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "services.coaching.opening.node.aannotate_moves",
                new=AsyncMock(side_effect=_fake_aannotate_moves),
            ),
            patch(
                "services.opening_deviation.deps.load_deps",
                wraps=opening_deviation_deps.load_deps,
                side_effect=_record_call_and_pass_through(call_order, "opening_deviation"),
            ),
            patch(
                "services.coaching.opening.opening_deps.load_deps",
                wraps=opening_deps.load_deps,
                side_effect=_record_call_and_pass_through(call_order, "opening"),
            ),
        ):
            with TestClient(app) as client:
                health_response = client.get("/health")
                self.assertEqual(health_response.status_code, 200)
                self.assertEqual(health_response.json(), {"status": "ok"})

                # A real route through the real DI graph -- not a hand-built
                # OpeningDeps. The Lichess fetch is faked to always miss, so
                # every position is OUT_OF_BOOK and the walk never covers a
                # single ply -- "book_unavailable" is the fully deterministic,
                # correct result of *this* fake, not an assumption.
                analyze_response = client.post(
                    "/opening/analyze",
                    json={"pgn": "1. e4 e5 2. Nf3 Nc6 *"},
                )

        self.assertEqual(analyze_response.status_code, 200)
        body = analyze_response.json()
        self.assertEqual(body["deviation"]["status"], "book_unavailable")
        self.assertEqual(body["critical_mistakes"], [])

        # The actual point of this test: fails immediately and specifically
        # if main.py's lifespan ever reverses these two calls -- rather than
        # relying on the indirect (if reliable) RuntimeError that reversing
        # them would also cause deeper in opening_deps.load_deps() itself.
        self.assertEqual(call_order, ["opening_deviation", "opening"])


if __name__ == "__main__":
    unittest.main()
