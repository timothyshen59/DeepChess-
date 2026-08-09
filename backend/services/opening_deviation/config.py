"""
Every configurable knob for the opening deviation engine, in one place. No
logic. A distinct `OPENING_DEVIATION_` env prefix is used deliberately: the
existing top-level `config.py::Settings` already has fields named
`deviation_share_threshold`/`mainline_share_threshold` for the older
Polyglot-book-based agent, and this module's settings must not silently
read from (or collide with) those same environment variables.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpeningDeviationSettings(BaseSettings):
    # `env_file=".env"` reads backend/.env for local dev (python-dotenv is
    # already an installed transitive dependency); a real process env var
    # -- e.g. a CI secret -- always takes priority over a colliding .env
    # entry, so the same settings class serves both without branching.
    # `populate_by_name=True` lets `lichess_api_token` (the one field with
    # a `validation_alias`, so it can be constructed directly by its
    # normal Python name too -- tests do this; env/`.env` loading still
    # only ever reads the bare LICHESS_API_TOKEN alias.
    model_config = SettingsConfigDict(
        env_prefix="OPENING_DEVIATION_", env_file=".env", extra="ignore", populate_by_name=True
    )

    # Frequency-tier classification thresholds.
    deviation_share_threshold: float = 0.01
    mainline_share_threshold: float = 0.10
    # Below this many total recorded games at a position, a percentage
    # share is statistical noise, not a real frequency -- classify as
    # OUT_OF_BOOK rather than falsely-confidently as a deviation.
    min_sample_games: int = 50

    # Lichess Opening Explorer client.
    explorer_base_url: str = "https://explorer.lichess.ovh"
    explorer_dataset: str = "masters"  # "masters" | "lichess"
    explorer_timeout_seconds: float = 5.0
    explorer_user_agent: str = "DeepChess-OpeningDeviationEngine/1.0"
    """Lichess's API etiquette asks clients to identify themselves; some
    endpoints reject requests carrying a generic/default User-Agent (e.g.
    httpx's own `python-httpx/<version>`) outright."""

    lichess_api_token: str | None = Field(default=None, validation_alias="LICHESS_API_TOKEN")
    """Personal Lichess API token (https://lichess.org/account/oauth/token).
    Optional -- the masters dataset works unauthenticated too, just at a
    lower rate limit. Read as the bare LICHESS_API_TOKEN env var,
    deliberately bypassing this module's own OPENING_DEVIATION_ prefix so
    it's one shared secret name across local .env files and CI, not a
    module-namespaced one."""

    explorer_max_retries: int = 3
    explorer_retry_backoff_seconds: float = 2.0
    """On a 429, retry up to `explorer_max_retries` times. Uses the
    response's `Retry-After` header when Lichess sends one; otherwise
    backs off `explorer_retry_backoff_seconds * 2**attempt` (2s, 4s,
    8s, ...). Lichess doesn't publish an exact number for this specific
    endpoint -- this is reactive recovery, not a substitute for pacing
    requests proactively (see `warmup_request_delay_seconds`)."""

    # Warmup crawl (run on demand, not at request time).
    warmup_max_ply: int = 30
    warmup_min_frequency_to_expand: float = 0.005
    warmup_target_position_count: int = 100_000
    warmup_request_delay_seconds: float = 1.0
    """Fixed pause between consecutive Explorer requests during the crawl
    -- paces requests to stay under Lichess's rate limit proactively
    (concurrency was already 1; the crawl had no throttling at all, which
    is the actual cause of getting rate-limited, not the concurrency
    level). 1 request/second is a conservative starting point, not a
    published Lichess number -- tune it down if you still get 429s, or up
    once you've observed you have headroom."""

    # Persistent local cache.
    cache_db_path: str = "services/opening_deviation/data/opening_cache.sqlite3"
    cache_max_size: int = 120_000


settings = OpeningDeviationSettings()
