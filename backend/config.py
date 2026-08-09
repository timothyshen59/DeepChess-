"""
Cross-cutting settings, introduced alongside the opening agent.

Existing services (`services/stockfish.py`, `services/transformer.py`) keep
their own scattered `os.getenv()` calls for now -- migrating them is a
separate, low-risk cleanup, not a prerequisite for this feature. New code
should read settings from here instead of adding a fourth scattered-getenv
site.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # Opening agent data sources.
    eco_index_path: str | None = None
    """Path to the ECO opening-name reference dataset. Falls back to the
    bundled seed dataset (services/coaching/opening/eco/data/eco_index.json)
    when unset."""

    # Opening agent timeouts (seconds), matching the plan's request budget.
    opening_branch_timeout_seconds: float = 3.0
    opening_total_timeout_seconds: float = 8.0
    opening_theory_max_plies: int = 30
    """How many plies of the game to compare against theory / evaluate with
    Stockfish. Openings are shallow, so this bounds both the deviation walk
    (services/opening_deviation) and the Stockfish batch to the phase
    that's actually relevant."""


settings = Settings()
