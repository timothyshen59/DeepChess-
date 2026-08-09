"""
Pure domain models for the opening deviation engine. No HTTP, no cache, no
classification logic lives here -- just the shapes every other layer passes
around, plus `canonical_fen_key`, the one piece of chess knowledge needed to
make the cache transposition-aware.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Classification = Literal["MAINLINE", "SIDELINE", "DEVIATION", "OUT_OF_BOOK"]


class CandidateMove(BaseModel):
    """One candidate next move at a position, with real game counts pulled
    straight from the Lichess Explorer API (or the cache mirroring it)."""

    uci: str
    san: str | None = None
    white: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)
    black: int = Field(default=0, ge=0)

    @property
    def total_games(self) -> int:
        return self.white + self.draws + self.black


class ExplorerStats(BaseModel):
    """Real Explorer statistics for a single position, already translated
    out of the raw API shape (see explorer/models.py)."""

    fen: str
    eco: str | None = None
    opening_name: str | None = None
    total_games: int = Field(ge=0)
    moves: list[CandidateMove] = Field(default_factory=list)


class MoveRecord(BaseModel):
    """The exact input contract the existing chess pipeline already
    produces per ply. This module consumes it as-is -- it does not
    reconstruct games or parse PGN itself."""

    position_fen: str
    next_move: str
    ply: int = Field(ge=1)


class ClassificationResult(BaseModel):
    """The output of classifying one (position, next_move) pair."""

    classification: Classification
    played_move_share: float | None = Field(default=None, ge=0.0, le=1.0)
    total_games: int = Field(ge=0)
    candidate_moves: list[CandidateMove] = Field(default_factory=list)
    best_move: CandidateMove | None = None


class DeviationResult(BaseModel):
    """The output of walking a full move sequence looking for the first
    real deviation."""

    found: bool
    ply: int | None = None
    position_fen: str | None = None
    played_move: str | None = None
    classification: ClassificationResult | None = None


def canonical_fen_key(fen: str) -> str:
    """Strip the halfmove-clock and fullmove-number fields from a FEN so
    transpositions -- the same position reached via a different move order
    -- naturally share one cache entry. Piece placement, side to move,
    castling rights, and the en passant target (FEN fields 1-4) together
    fully determine legal continuations from here; the trailing clock
    fields never should.
    """
    fields = fen.split()
    return " ".join(fields[:4])
