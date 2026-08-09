from __future__ import annotations

from .. import schemas
from ..state import OpeningState


def build_report(state: OpeningState) -> schemas.OpeningReport:
    """Assemble the final OpeningReport from every branch's output."""
    branch_results = state.get("branch_results", {})

    return schemas.OpeningReport(
        opening=state.get("opening", schemas.OpeningIdentity()),
        deviation=state["deviation"],
        critical_mistakes=branch_results.get("critical_mistakes", []),
        strategic_themes=branch_results.get("strategic_themes", []),
        middlegame_plans=branch_results.get("middlegame_plans", []),
        model_games=branch_results.get("model_games", []),
        input_issues=state.get("input_issues", []),
    )
