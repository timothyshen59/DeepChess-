from __future__ import annotations

from .schemas import CombinedLesson

DEFAULT_LESSON_LIMIT = 10


def rank_and_select(
    lessons: list[CombinedLesson],
    limit: int = DEFAULT_LESSON_LIMIT,
) -> list[CombinedLesson]:
    """Sort by cp_loss descending; keep at most `limit`.

    A stable sort preserves encounter order among ties -- no re-scoring, no
    secondary tie-breaking heuristics.
    """
    ranked = sorted(lessons, key=lambda lesson: lesson.cp_loss, reverse=True)
    return ranked[:limit]
