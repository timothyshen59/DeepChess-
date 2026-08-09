from __future__ import annotations

from typing import TypedDict

from services.coaching.opening.schemas import OpeningReport
from services.coaching.tactics.schemas import TacticsReport

from .schemas import CombinedLesson, CoordinatedReport, InputIssue


class CoordinatorState(TypedDict, total=False):
    """State for the coordinator workflow.

    `opening_report`/`tactics_report` are read-only inputs -- the
    coordinator never calls either agent, only consumes their already-built
    reports. No Annotated reducer is used anywhere here: every node is
    strictly sequential, so there is no parallel fan-out writing to a
    shared key (unlike opening/state.py's merge_branch_results or
    tactics/state.py's merge_feature_updates).
    """

    opening_report: OpeningReport | None
    tactics_report: TacticsReport | None

    input_issues: list[InputIssue]
    combined_lessons: list[CombinedLesson]
    ranked_lessons: list[CombinedLesson]
    tactical_habit_summary: tuple[str, list[str]]

    report: CoordinatedReport
