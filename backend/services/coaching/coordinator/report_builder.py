"""
Assembles the final CoordinatedReport. Rule-based assembly only -- no new
analysis, no re-scoring, no engine calls.
"""

from __future__ import annotations

from services.coaching.opening.schemas import OpeningReport

from .schemas import CombinedLesson, CoordinatedReport, InputIssue, OpeningSummary


def assemble_report(
    opening_report: OpeningReport | None,
    ranked_lessons: list[CombinedLesson],
    recurring_pattern: str,
    tactical_habits: list[str],
    input_issues: list[InputIssue],
) -> CoordinatedReport:
    opening_summary = None

    if opening_report is not None:
        opening_summary = OpeningSummary(
            opening=opening_report.opening,
            deviation=opening_report.deviation,
            strategic_themes=opening_report.strategic_themes,
            middlegame_plans=opening_report.middlegame_plans,
            model_games=opening_report.model_games,
        )

    if recurring_pattern:
        final_pattern = recurring_pattern
    elif ranked_lessons:
        final_pattern = "Review the ranked lessons below for the game's most significant moments."
    else:
        final_pattern = "No notable mistakes found."

    return CoordinatedReport(
        lessons=ranked_lessons,
        recurring_pattern=final_pattern,
        tactical_habits=tactical_habits,
        opening_summary=opening_summary,
        input_issues=input_issues,
    )
