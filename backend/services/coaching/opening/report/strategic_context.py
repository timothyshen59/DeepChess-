"""
Curated, rule-based strategic themes and middlegame plans, keyed by ECO.

No LLM in v1 (see architecture plan decision #1), same rule-based approach
as tactics/report/tactical_rules.py's motif-keyed templates, just keyed by
opening (ECO code, falling back to the ECO family letter) instead of by
tactical motif. Seed content for the Najdorf entry below is taken verbatim
from plan.md's own worked example.
"""

from __future__ import annotations

from ..schemas import MiddlegamePlan, StrategicTheme

_THEMES_BY_ECO: dict[str, list[StrategicTheme]] = {
    "B90": [
        StrategicTheme(
            title="Contest the center",
            description="Challenge White's central pawn duo with ...e5 or ...d5.",
        ),
        StrategicTheme(
            title="Development tempo",
            description="Prioritize rapid minor piece development over extra pawn moves.",
        ),
        StrategicTheme(
            title="King safety",
            description="Castle early and connect the rooks.",
        ),
        StrategicTheme(
            title="Queenside expansion",
            description="Expand on the queenside with ...b5 and pressure the c-file.",
        ),
        StrategicTheme(
            title="Key square",
            description="Control the d5 square.",
        ),
    ],
    "C65": [
        StrategicTheme(
            title="Simplified structure",
            description="The Berlin's symmetrical structure rewards small technical edges over sharp attacks.",
        ),
        StrategicTheme(
            title="Piece activity",
            description="Piece activity matters more than the (often doubled/isolated) pawn structure.",
        ),
    ],
}

_THEMES_BY_FAMILY: dict[str, list[StrategicTheme]] = {
    "A": [
        StrategicTheme(
            title="Flexible structure",
            description="Flank openings delay central pawn commitments; decide the structure with piece play first.",
        ),
    ],
    "B": [
        StrategicTheme(
            title="Asymmetry",
            description="Semi-open games produce asymmetrical pawn structures; know the typical pawn breaks for your side.",
        ),
    ],
    "C": [
        StrategicTheme(
            title="Rapid development",
            description="Open games reward fast development and early king safety over slow maneuvering.",
        ),
    ],
    "D": [
        StrategicTheme(
            title="Pawn-structure decisions",
            description="Closed queen's-pawn games often hinge on IQP/hanging-pawn structures and minority attacks.",
        ),
    ],
    "E": [
        StrategicTheme(
            title="Fight for the center with pieces",
            description="Indian systems contest the center with piece pressure before committing central pawns.",
        ),
    ],
}

_PLANS_BY_ECO: dict[str, list[MiddlegamePlan]] = {
    "B90": [
        MiddlegamePlan(
            side="black",
            plans=[
                "Expand with ...b5",
                "Pressure the c-file with the rooks",
                "Challenge the center with ...e5 or ...d5",
                "Create queenside counterplay",
            ],
        ),
        MiddlegamePlan(
            side="white",
            plans=[
                "Expand on the kingside with f4",
                "Maintain central space",
                "Launch a kingside attack",
                "Restrict Black's queenside play",
            ],
        ),
    ],
    "C65": [
        MiddlegamePlan(
            side="white",
            plans=[
                "Press for a small structural edge in the resulting endgame",
                "Trade into favorable minor-piece endings",
            ],
        ),
        MiddlegamePlan(
            side="black",
            plans=[
                "Neutralize White's space advantage with active piece play",
                "Aim for simplification if no concrete edge is available",
            ],
        ),
    ],
}


def get_strategic_context(eco: str | None) -> tuple[list[StrategicTheme], list[MiddlegamePlan]]:
    """Return (themes, middlegame plans) for an ECO code.

    Falls back to a generic template for the opening's ECO family (first
    letter) when there's no opening-specific entry, and to an empty result
    when the ECO code itself is unknown.
    """
    if not eco:
        return [], []

    themes = _THEMES_BY_ECO.get(eco) or _THEMES_BY_FAMILY.get(eco[0], [])
    plans = _PLANS_BY_ECO.get(eco, [])

    return themes, plans
