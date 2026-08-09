"""
Identifies the opening, finds where the player left known theory, flags
objective opening-phase mistakes, and returns strategic themes / typical
middlegame plans / model games for the opening.

The first async route in the repo -- see
services/coaching/opening/graph.py for why: `evaluate_mistakes` is the only
node doing real, slow work (a batched Stockfish evaluation), so the graph
runs it concurrently with the two static-lookup branches via `.ainvoke()`
instead of serially.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.coaching.opening import opening_deps
from services.coaching.opening.schemas import OpeningReport

router = APIRouter()


class OpeningAnalyzeRequest(BaseModel):
    pgn: str
    fen: str | None = None
    user_color: str | None = None


@router.post("/opening/analyze", response_model=OpeningReport)
async def analyze_opening(request: OpeningAnalyzeRequest) -> OpeningReport:
    graph = opening_deps.get_graph()

    result = await graph.ainvoke({
        "pgn": request.pgn,
        "fen": request.fen,
        "user_color": request.user_color,
    })

    report = result.get("report")

    if report is None:
        raise HTTPException(status_code=400, detail="Could not analyze the supplied PGN.")

    return report
