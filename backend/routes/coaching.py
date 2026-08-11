"""
Exposes the full coaching pipeline (opening agent -> tactics agent ->
coordinator) over HTTP.

services.coaching.pipeline.run_coaching_pipeline already existed and is
the most-tested part of the backend (tests/e2e/test_coaching_pipeline.py),
but until now it was only ever called directly in Python by that test --
no route wired it up, so a frontend had no way to get a merged
opening+tactics+coordinator report. Every other route exposes at most one
agent (`/analyze` is raw Stockfish annotation, `/opening/analyze` is the
opening agent alone). This mirrors `routes/opening.py`'s DI pattern:
`run_coaching_pipeline`'s own docstring already documents production
callers as passing `opening_deps.get_deps()`, this is just the first route
to actually do it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.coaching.coordinator.schemas import CoordinatedReport
from services.coaching.opening import opening_deps
from services.coaching.opening.schemas import OpeningReport
from services.coaching.pipeline import run_coaching_pipeline
from services.coaching.tactics.schemas import TacticsReport
from services.pgn_utils import InvalidPgnError

router = APIRouter()


class CoachingAnalyzeRequest(BaseModel):
    pgn: str


class CoachingAnalyzeResponse(BaseModel):
    coordinated: CoordinatedReport
    opening: OpeningReport
    tactics: TacticsReport


@router.post("/coaching/analyze", response_model=CoachingAnalyzeResponse)
async def analyze_coaching(request: CoachingAnalyzeRequest) -> CoachingAnalyzeResponse:
    try:
        result = await run_coaching_pipeline(request.pgn, opening_deps.get_deps())
    except InvalidPgnError as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid PGN. Check the notation and try again.",
        ) from error

    return CoachingAnalyzeResponse(
        coordinated=result.coordinated,
        opening=result.opening,
        tactics=result.tactics,
    )
