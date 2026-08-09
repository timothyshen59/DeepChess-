"""
Input validation for the coordinator.

Checks presence/shape of the two source reports and forwards their own
upstream input_issues -- performs no chess analysis of any kind.
"""

from __future__ import annotations

from services.coaching.opening.schemas import OpeningReport
from services.coaching.tactics.schemas import TacticsReport

from .schemas import InputIssue


def validate_reports(
    opening_report: OpeningReport | None,
    tactics_report: TacticsReport | None,
) -> list[InputIssue]:
    """Check incoming reports are usable and carry forward their issues."""
    issues: list[InputIssue] = []

    if opening_report is None:
        issues.append(
            InputIssue(
                code="missing_opening_report",
                message="No opening report was supplied; opening-derived lessons are unavailable.",
                severity="warning",
            )
        )
    else:
        issues.extend(_carry_forward(opening_report.input_issues, source="opening"))

    if tactics_report is None:
        issues.append(
            InputIssue(
                code="missing_tactics_report",
                message="No tactics report was supplied; tactical lessons are unavailable.",
                severity="warning",
            )
        )
    else:
        issues.extend(_carry_forward(tactics_report.input_issues, source="tactics"))

    return issues


def _carry_forward(source_issues, source: str) -> list[InputIssue]:
    return [
        InputIssue(
            ply=issue.ply,
            code=f"{source}:{issue.code}",
            message=issue.message,
            severity=issue.severity,
        )
        for issue in source_issues
    ]
