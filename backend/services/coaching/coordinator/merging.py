"""
Exact-key matching and merging of opening mistakes with tactical lessons.

Matching is a plain dict lookup on (ply, move_number, player_color) -- no
fuzzy matching, no SAN comparison, no board reconstruction, per the
architecture plan.
"""

from __future__ import annotations

from services.coaching.opening.schemas import CriticalMistake as OpeningCriticalMistake
from services.coaching.tactics.schemas import TacticalLesson

from .schemas import CombinedLesson, ColorName, InputIssue, LessonSource

LessonKey = tuple[int, int, ColorName]


def _opening_key(mistake: OpeningCriticalMistake) -> LessonKey:
    return (mistake.ply, mistake.move_number, mistake.player_color)


def _tactics_key(lesson: TacticalLesson) -> LessonKey:
    return (lesson.ply, lesson.move_number, lesson.player_color)


def merge_lessons(
    opening_mistakes: list[OpeningCriticalMistake],
    tactical_lessons: list[TacticalLesson],
) -> tuple[list[CombinedLesson], list[InputIssue]]:
    """Merge two mistake lists into one, deduplicating by exact key.

    A key present in both sources becomes one CombinedLesson with
    source="both"; a key present in only one source becomes a standalone
    CombinedLesson with source="opening"/"tactics".
    """
    opening_by_key = {_opening_key(mistake): mistake for mistake in opening_mistakes}
    tactics_by_key = {_tactics_key(lesson): lesson for lesson in tactical_lessons}

    # dict.fromkeys preserves first-seen order (opening keys first) while
    # deduplicating keys that appear in both.
    all_keys = list(dict.fromkeys([*opening_by_key.keys(), *tactics_by_key.keys()]))

    combined: list[CombinedLesson] = []
    issues: list[InputIssue] = []

    for key in all_keys:
        ply, move_number, player_color = key
        opening_mistake = opening_by_key.get(key)
        tactical_lesson = tactics_by_key.get(key)

        source: LessonSource

        if opening_mistake is not None and tactical_lesson is not None:
            source = "both"
            cp_loss = opening_mistake.cp_loss
            played_move = opening_mistake.played_san

            if opening_mistake.played_san != tactical_lesson.played_move:
                issues.append(
                    InputIssue(
                        ply=ply,
                        code="played_move_mismatch",
                        message=(
                            f"Opening and tactics reports disagree on the move played "
                            f"at ply {ply} ('{opening_mistake.played_san}' vs "
                            f"'{tactical_lesson.played_move}'); the two reports may not "
                            f"describe the same game."
                        ),
                        severity="warning",
                    )
                )
        elif opening_mistake is not None:
            source = "opening"
            cp_loss = opening_mistake.cp_loss
            played_move = opening_mistake.played_san
        else:
            # all_keys only ever contains keys present in at least one of
            # the two source dicts -- reaching here means opening_mistake
            # was None, so tactical_lesson must be the one that's real.
            assert tactical_lesson is not None
            source = "tactics"
            cp_loss = tactical_lesson.cp_loss
            played_move = tactical_lesson.played_move

        combined.append(
            CombinedLesson(
                ply=ply,
                move_number=move_number,
                player_color=player_color,
                played_move=played_move,
                cp_loss=cp_loss,
                source=source,
                opening_mistake=opening_mistake,
                tactical_lesson=tactical_lesson,
            )
        )

    return combined, issues
