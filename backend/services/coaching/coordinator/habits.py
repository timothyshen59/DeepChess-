"""
Aggregates tactical habits from lessons that didn't make the final ranked
list, so they still shape the coaching narrative without being shown as
individual lessons.
"""

from __future__ import annotations

from services.coaching.tactics.schemas import TacticsReport

from .merging import LessonKey


def summarize_dropped_tactics(
    tactics_report: TacticsReport | None,
    kept_keys: set[LessonKey],
) -> tuple[str, list[str]]:
    """Aggregate calculation habits from tactics lessons not in `kept_keys`.

    Operates on the FULL tactics_report.crucial_mistakes (already capped at
    4 by the tactics agent itself), independent of what actually survived
    into the coordinator's final ranked output.
    """
    if tactics_report is None:
        return "", []

    dropped = [
        lesson
        for lesson in tactics_report.crucial_mistakes
        if (lesson.ply, lesson.move_number, lesson.player_color) not in kept_keys
    ]

    habits = list(dict.fromkeys(lesson.calculation_habit for lesson in dropped))

    return tactics_report.recurring_pattern, habits
