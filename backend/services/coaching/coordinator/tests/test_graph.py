"""
Unit tests for the coordinator.

No PGN, no Stockfish, no real opening/tactics graphs -- the coordinator
only ever consumes already-built report objects, so fake ones are
constructed directly. Some edge cases (>10 combined entries, tactics
lessons dropped from the final list) can't be reached through a full
graph invocation because OpeningReport.critical_mistakes and
TacticsReport.crucial_mistakes are each already capped at 4 upstream (see
the architecture plan's "Migration Risks" section) -- those are tested by
calling ranking.py/habits.py directly instead.
"""

from __future__ import annotations

import unittest

from services.coaching.opening.schemas import CriticalMistake as OpeningCriticalMistake
from services.coaching.opening.schemas import Deviation, OpeningIdentity, OpeningReport
from services.coaching.tactics.schemas import TacticalLesson, TacticsReport

from services.coaching.coordinator.graph import build_coordinator_graph
from services.coaching.coordinator.habits import summarize_dropped_tactics
from services.coaching.coordinator.ranking import rank_and_select
from services.coaching.coordinator.schemas import CombinedLesson


def _opening_report(mistakes: list[OpeningCriticalMistake]) -> OpeningReport:
    return OpeningReport(
        opening=OpeningIdentity(eco="B90", name="Sicilian Defense", variation="Najdorf Variation"),
        deviation=Deviation(status="followed_theory"),
        critical_mistakes=mistakes,
    )


def _tactics_report(lessons: list[TacticalLesson]) -> TacticsReport:
    return TacticsReport(
        headline="Sample headline",
        recurring_pattern="Sample recurring pattern",
        crucial_mistakes=lessons,
    )


def _opening_mistake(ply: int, move_number: int, color: str, played_san: str, cp_loss: int) -> OpeningCriticalMistake:
    return OpeningCriticalMistake(
        ply=ply,
        move_number=move_number,
        player_color=color,
        played_san=played_san,
        best_move_san="Be7",
        cp_loss=cp_loss,
        severity="mistake",
        explanation="Sample opening explanation.",
    )


def _tactical_lesson(ply: int, move_number: int, color: str, played_move: str, cp_loss: int) -> TacticalLesson:
    return TacticalLesson(
        ply=ply,
        move_number=move_number,
        player_color=color,
        category="offensive",
        motif="hanging_piece",
        played_move=played_move,
        cp_loss=cp_loss,
        explanation="Sample tactical explanation.",
        calculation_habit="Check for hanging pieces before moving.",
        confidence="high",
    )


class CoordinatorGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = build_coordinator_graph()

    def test_merges_overlapping_key_into_one_lesson(self) -> None:
        opening_report = _opening_report([_opening_mistake(14, 7, "black", "h6", 27)])
        tactics_report = _tactics_report([_tactical_lesson(14, 7, "black", "h6", 27)])

        result = self.graph.invoke({
            "opening_report": opening_report,
            "tactics_report": tactics_report,
        })
        report = result["report"]

        self.assertEqual(len(report.lessons), 1)
        lesson = report.lessons[0]
        self.assertEqual(lesson.source, "both")
        self.assertEqual(lesson.cp_loss, 27)
        self.assertIsNotNone(lesson.opening_mistake)
        self.assertIsNotNone(lesson.tactical_lesson)
        self.assertEqual(report.input_issues, [])

    def test_keeps_standalone_entries_when_no_overlap(self) -> None:
        opening_report = _opening_report([_opening_mistake(11, 6, "white", "Be2", 40)])
        tactics_report = _tactics_report([_tactical_lesson(19, 10, "white", "f4", 26)])

        result = self.graph.invoke({
            "opening_report": opening_report,
            "tactics_report": tactics_report,
        })
        report = result["report"]

        self.assertEqual(len(report.lessons), 2)
        sources = {lesson.source for lesson in report.lessons}
        self.assertEqual(sources, {"opening", "tactics"})
        # Ranked descending by cp_loss.
        self.assertEqual([lesson.cp_loss for lesson in report.lessons], [40, 26])

    def test_missing_tactics_report_still_produces_a_report(self) -> None:
        opening_report = _opening_report([_opening_mistake(14, 7, "black", "h6", 27)])

        result = self.graph.invoke({
            "opening_report": opening_report,
            "tactics_report": None,
        })
        report = result["report"]

        self.assertEqual(len(report.lessons), 1)
        self.assertEqual(report.lessons[0].source, "opening")
        self.assertTrue(
            any(issue.code == "missing_tactics_report" for issue in report.input_issues)
        )

    def test_missing_both_reports_produces_empty_report_without_crashing(self) -> None:
        result = self.graph.invoke({"opening_report": None, "tactics_report": None})
        report = result["report"]

        self.assertEqual(report.lessons, [])
        self.assertEqual(report.recurring_pattern, "No notable mistakes found.")
        self.assertEqual(len(report.input_issues), 2)

    def test_flags_played_move_mismatch_but_still_merges(self) -> None:
        opening_report = _opening_report([_opening_mistake(14, 7, "black", "h6", 27)])
        tactics_report = _tactics_report([_tactical_lesson(14, 7, "black", "Nbd7", 27)])

        result = self.graph.invoke({
            "opening_report": opening_report,
            "tactics_report": tactics_report,
        })
        report = result["report"]

        self.assertEqual(len(report.lessons), 1)
        self.assertEqual(report.lessons[0].source, "both")
        mismatch_issues = [i for i in report.input_issues if i.code == "played_move_mismatch"]
        self.assertEqual(len(mismatch_issues), 1)
        self.assertEqual(mismatch_issues[0].severity, "warning")


class RankingUnitTests(unittest.TestCase):
    """Exercises the >10-entries truncation path directly, since neither
    source report can actually be constructed with more than 4 mistakes
    (see module docstring)."""

    def test_truncates_to_ten_highest_cp_loss(self) -> None:
        lessons = [
            CombinedLesson(
                ply=i, move_number=i, player_color="white",
                played_move="e4", cp_loss=i, source="opening",
            )
            for i in range(1, 13)  # 12 entries, cp_loss 1..12
        ]

        ranked = rank_and_select(lessons)

        self.assertEqual(len(ranked), 10)
        self.assertEqual([lesson.cp_loss for lesson in ranked], list(range(12, 2, -1)))


class TacticalHabitAggregationTests(unittest.TestCase):
    """Exercises the "dropped tactics lesson" aggregation path directly,
    since it can't be forced via the full graph under current caps."""

    def test_dropped_lessons_contribute_habits_without_being_shown(self) -> None:
        kept = _tactical_lesson(1, 1, "white", "e4", 10)
        dropped = _tactical_lesson(3, 2, "white", "Nf3", 5)
        dropped.calculation_habit = "Always double-check for forks."

        tactics_report = _tactics_report([kept, dropped])
        kept_keys = {(kept.ply, kept.move_number, kept.player_color)}

        recurring_pattern, habits = summarize_dropped_tactics(tactics_report, kept_keys)

        self.assertEqual(recurring_pattern, "Sample recurring pattern")
        self.assertEqual(habits, ["Always double-check for forks."])

    def test_no_tactics_report_returns_empty_summary(self) -> None:
        recurring_pattern, habits = summarize_dropped_tactics(None, set())

        self.assertEqual(recurring_pattern, "")
        self.assertEqual(habits, [])


if __name__ == "__main__":
    unittest.main()
