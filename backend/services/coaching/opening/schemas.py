from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from services.opening_deviation.models.opening import Classification

ColorName = Literal["white", "black"]
DeviationStatus = Literal[
    "deviated",
    "followed_theory",
    "book_unavailable",
    "insufficient_moves",
]
MistakeSeverity = Literal["mistake", "blunder"]


class InputIssue(BaseModel):
    """Mirrors tactics/schemas.py::InputIssue's shape.

    Deliberately duplicated rather than imported: coaching sub-features stay
    decoupled from one another, same as tactics doesn't import from opening.
    """

    ply: int | None = None
    code: str
    message: str
    severity: Literal["warning", "error"] = "error"


class OpeningIdentity(BaseModel):
    eco: str | None = None
    name: str | None = None
    variation: str | None = None
    matched_plies: int = Field(default=0, ge=0)


class Deviation(BaseModel):
    status: DeviationStatus
    ply: int | None = None
    move_number: int | None = None
    player_color: ColorName | None = None
    played_san: str | None = None
    better_move_san: str | None = None
    better_move_uci: str | None = None
    better_line_san: list[str] = Field(default_factory=list)
    note: str = ""

    played_move_share: float | None = Field(default=None, ge=0.0, le=1.0)
    """What fraction of real games at the deviation ply played the move
    actually played -- 0.0 if no recorded game played it at all. Only set
    when status == "deviated"."""

    theory_tier: Classification | None = None
    """The Opening Deviation Engine's classification of the played move at
    the deviation ply (services/opening_deviation) -- see its
    OpeningDeviationSettings for the underlying thresholds. Only set when
    status == "deviated"."""


class CriticalMistake(BaseModel):
    ply: int = Field(ge=1)
    move_number: int = Field(ge=1)
    player_color: ColorName
    played_san: str
    best_move_san: str | None = None
    cp_loss: int = Field(ge=0)
    severity: MistakeSeverity
    explanation: str = Field(min_length=1, max_length=500)


class StrategicTheme(BaseModel):
    title: str
    description: str


class MiddlegamePlan(BaseModel):
    side: ColorName
    plans: list[str] = Field(default_factory=list)


class ModelGameRef(BaseModel):
    white: str
    black: str
    event: str | None = None
    year: int | None = None
    eco: str


class OpeningReport(BaseModel):
    opening: OpeningIdentity
    deviation: Deviation
    critical_mistakes: list[CriticalMistake] = Field(default_factory=list, max_length=4)
    strategic_themes: list[StrategicTheme] = Field(default_factory=list)
    middlegame_plans: list[MiddlegamePlan] = Field(default_factory=list)
    model_games: list[ModelGameRef] = Field(default_factory=list)
    input_issues: list[InputIssue] = Field(default_factory=list)
