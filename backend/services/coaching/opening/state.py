from __future__ import annotations

from typing import Annotated, TypedDict

from .schemas import (
    CriticalMistake,
    Deviation,
    InputIssue,
    MiddlegamePlan,
    ModelGameRef,
    OpeningIdentity,
    OpeningReport,
    StrategicTheme,
)


class BranchResults(TypedDict, total=False):
    """Output of the three parallel post-deviation branches.

    Unlike tactics' `feature_updates` (where several branches write features
    for the *same* ply and need a per-ply deep merge), each branch here
    writes to its own disjoint key — `evaluate_mistakes` only ever sets
    `critical_mistakes`, `fetch_model_games` only `model_games`, and
    `fetch_strategic_context` sets both theme keys. The merge is therefore a
    plain dict union, not a per-ply merge.
    """

    critical_mistakes: list[CriticalMistake]
    model_games: list[ModelGameRef]
    strategic_themes: list[StrategicTheme]
    middlegame_plans: list[MiddlegamePlan]


def merge_branch_results(current: BranchResults, incoming: BranchResults) -> BranchResults:
    """Union independent parallel-branch outputs by key."""
    merged: BranchResults = {**current}
    merged.update(incoming)
    return merged


class OpeningState(TypedDict, total=False):
    """State for the opening coaching workflow."""

    pgn: str
    fen: str | None
    user_color: str | None

    moves: list[dict]
    input_issues: list[InputIssue]

    opening: OpeningIdentity
    deviation: Deviation

    branch_results: Annotated[BranchResults, merge_branch_results]

    report: OpeningReport
