from __future__ import annotations

from ..schemas import InputIssue, TacticalLesson, TacticsReport


def build_report(
    lessons: list[TacticalLesson],
    input_issues: list[InputIssue],
) -> TacticsReport:
    """Build a game-level report from already-ranked tactical lessons."""
    selected_lessons = lessons[:4]

    defensive_count = sum(
        lesson.category in {"defensive", "mixed"}
        for lesson in selected_lessons
    )
    offensive_count = sum(
        lesson.category in {"offensive", "mixed"}
        for lesson in selected_lessons
    )

    if not selected_lessons:
        headline = "No verified tactical blunders found"
        recurring_pattern = (
            "The supplied annotations did not contain a legal move with a "
            "sufficiently large evaluation loss or tactical signal."
        )
    elif defensive_count > offensive_count:
        headline = "The main issue was defensive tactical awareness"
        recurring_pattern = (
            "Several errors came from not checking the opponent's immediate "
            "checks, captures, and mating threats after your intended move."
        )
    elif offensive_count > defensive_count:
        headline = "The main issue was missing forcing opportunities"
        recurring_pattern = (
            "The strongest continuations were often forcing checks or captures "
            "that should be considered before quieter alternatives."
        )
    else:
        headline = "The game contained both attacking and defensive tactical misses"
        recurring_pattern = (
            "Use a balanced tactical scan: calculate your checks and captures, "
            "then verify the opponent's immediate checks, captures, and threats."
        )

    return TacticsReport(
        headline=headline,
        recurring_pattern=recurring_pattern,
        crucial_mistakes=selected_lessons,
        input_issues=input_issues,
    )