"""
The raw Lichess Opening Explorer API response shape, isolated from the rest
of the system, plus the translation into our own domain model.

The exact field names below are a documented ASSUMPTION, not verified
against a live call -- per the architecture plan's "Assumptions" section.
If the real API differs, this is the one file that needs to change.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models.opening import CandidateMove, ExplorerStats


class ExplorerApiMove(BaseModel):
    uci: str
    san: str | None = None
    white: int = 0
    draws: int = 0
    black: int = 0


class ExplorerApiOpening(BaseModel):
    eco: str | None = None
    name: str | None = None


class ExplorerApiResponse(BaseModel):
    white: int = 0
    draws: int = 0
    black: int = 0
    moves: list[ExplorerApiMove] = Field(default_factory=list)
    opening: ExplorerApiOpening | None = None


def to_explorer_stats(fen: str, raw: ExplorerApiResponse) -> ExplorerStats:
    """Translate the raw API shape into our domain model. The position's
    total game count comes from the top-level white/draws/black -- the
    aggregate across every game that reached this position, regardless of
    which move they played next.
    """
    return ExplorerStats(
        fen=fen,
        eco=raw.opening.eco if raw.opening else None,
        opening_name=raw.opening.name if raw.opening else None,
        total_games=raw.white + raw.draws + raw.black,
        moves=[
            CandidateMove(uci=move.uci, san=move.san, white=move.white, draws=move.draws, black=move.black)
            for move in raw.moves
        ],
    )
