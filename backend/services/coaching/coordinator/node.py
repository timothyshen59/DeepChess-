from __future__ import annotations

from .habits import summarize_dropped_tactics
from .merging import merge_lessons
from .ranking import rank_and_select
from .report_builder import assemble_report
from .state import CoordinatorState
from .validation import validate_reports


def validate_inputs(state: CoordinatorState) -> dict:
    issues = validate_reports(
        state.get("opening_report"),
        state.get("tactics_report"),
    )
    return {"input_issues": issues}


def normalize_and_merge(state: CoordinatorState) -> dict:
    opening_report = state.get("opening_report")
    tactics_report = state.get("tactics_report")

    opening_mistakes = opening_report.critical_mistakes if opening_report else []
    tactical_lessons = tactics_report.crucial_mistakes if tactics_report else []

    combined, merge_issues = merge_lessons(opening_mistakes, tactical_lessons)

    return {
        "combined_lessons": combined,
        "input_issues": [*state.get("input_issues", []), *merge_issues],
    }


def rank_lessons(state: CoordinatorState) -> dict:
    ranked = rank_and_select(state.get("combined_lessons", []))
    return {"ranked_lessons": ranked}


def aggregate_tactical_habits(state: CoordinatorState) -> dict:
    kept_keys = {
        (lesson.ply, lesson.move_number, lesson.player_color)
        for lesson in state.get("ranked_lessons", [])
    }
    summary = summarize_dropped_tactics(state.get("tactics_report"), kept_keys)
    return {"tactical_habit_summary": summary}


def assemble_report_node(state: CoordinatorState) -> dict:
    recurring_pattern, tactical_habits = state.get("tactical_habit_summary", ("", []))

    report = assemble_report(
        opening_report=state.get("opening_report"),
        ranked_lessons=state.get("ranked_lessons", []),
        recurring_pattern=recurring_pattern,
        tactical_habits=tactical_habits,
        input_issues=state.get("input_issues", []),
    )
    return {"report": report}
