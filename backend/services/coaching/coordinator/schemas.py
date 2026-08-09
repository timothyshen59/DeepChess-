"""
Domain models for the coordinator layer.

Pure data only -- no methods, no computed properties, no validators beyond
field constraints. Any picking/derivation logic (e.g. which source's
cp_loss wins when both agents flag the same move) lives in merging.py, not
here. See the architecture plan's Design Decision #2.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from services.coaching.opening.schemas import (
    Deviation,
    MiddlegamePlan,
    ModelGameRef,
    OpeningIdentity,
    StrategicTheme,
)
from services.coaching.opening.schemas import CriticalMistake as OpeningCriticalMistake
from services.coaching.tactics.schemas import TacticalLesson

ColorName = Literal["white", "black"]
LessonSource = Literal["opening", "tactics", "both"]


class InputIssue(BaseModel):
    """Coordinator-local input issue.

    Structurally identical to the classes independently defined in
    opening/schemas.py and tactics/schemas.py -- deliberately not unified;
    see the architecture plan's "Migration Risks" section.
    """

    ply: int | None = None
    code: str
    message: str
    severity: Literal["warning", "error"] = "error"


class CombinedLesson(BaseModel):
    """One coaching lesson, backed by one or both source agents.

    Nests the ORIGINAL opening/tactics objects verbatim rather than
    redefining slim mirror types -- see architecture plan Design Decision #1.
    """

    ply: int = Field(ge=1)
    move_number: int = Field(ge=1)
    player_color: ColorName
    played_move: str
    cp_loss: int = Field(ge=0)
    source: LessonSource

    opening_mistake: OpeningCriticalMistake | None = None
    tactical_lesson: TacticalLesson | None = None


class OpeningSummary(BaseModel):
    """Pass-through subset of OpeningReport unrelated to "mistakes" --
    untouched, carried forward as-is into the combined report."""

    opening: OpeningIdentity
    deviation: Deviation
    strategic_themes: list[StrategicTheme] = Field(default_factory=list)
    middlegame_plans: list[MiddlegamePlan] = Field(default_factory=list)
    model_games: list[ModelGameRef] = Field(default_factory=list)


class CoordinatedReport(BaseModel):
    lessons: list[CombinedLesson] = Field(default_factory=list, max_length=10)
    recurring_pattern: str = ""
    tactical_habits: list[str] = Field(default_factory=list)
    opening_summary: OpeningSummary | None = None
    input_issues: list[InputIssue] = Field(default_factory=list)
