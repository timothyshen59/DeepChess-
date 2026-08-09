from __future__ import annotations

from typing import TypedDict

from .opening.schemas import OpeningReport
from .tactics.schemas import AnnotatedMove, TacticsReport


class CoachingState(TypedDict, total=False):
    """Top-level coaching state.

    Keep this boundary intentionally small: game ingestion can populate
    `annotated_moves`, while the tactics subgraph produces `tactics_report`
    and the opening subgraph produces `opening_report`.
    """

    annotated_moves: list[AnnotatedMove]
    tactics_report: TacticsReport
    opening_report: OpeningReport

