from __future__ import annotations

from typing import Annotated, TypedDict

from .schemas import (
    AnnotatedMove,
    CandidateFeatures,
    InputIssue,
    TacticalCandidate,
    TacticsReport,
    TacticalLesson,
)

from .strategic.models import StrategicFact


def merge_feature_updates(
    current: dict[int, CandidateFeatures], incoming: dict[int, CandidateFeatures]
) -> dict[int, CandidateFeatures]:
    """Deep-merge independent parallel feature branch outputs by ply."""
    merged = dict(current)

    for ply, update in incoming.items():
        existing = merged.get(ply, CandidateFeatures())
        merged[ply] = existing.model_copy(
            update={
                "best_move": update.best_move or existing.best_move,
                "played_move": update.played_move or existing.played_move,
                "played_defense": update.played_defense or existing.played_defense,
                "principal_variation": update.principal_variation or existing.principal_variation,
            }
        )

    return merged


class TacticsState(TypedDict, total=False):
    """State for the tactics coaching workflow.

    `feature_updates` is written by three independent graph branches. LangGraph
    can therefore execute the best-move, played-position, and PV inspection
    nodes concurrently.
    """

    annotated_moves: list[AnnotatedMove]
    valid_moves: list[AnnotatedMove]
    candidates: list[TacticalCandidate]
    input_issues: list[InputIssue]
    feature_updates: Annotated[
        dict[int, CandidateFeatures],
        merge_feature_updates,
    ]

    strategic_facts_by_ply: dict[int, tuple[StrategicFact, ...]]
    lessons: list[TacticalLesson]

    report: TacticsReport
