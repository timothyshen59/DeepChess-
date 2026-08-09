"""
HTTP boundary for the opening deviation engine. All business logic
(caching, classification, the Explorer client) lives in
services/opening_deviation/ -- this file only translates HTTP <-> the
service layer, matching the pattern already established by
routes/opening.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.opening_deviation import deps
from services.opening_deviation.models.opening import (
    ClassificationResult,
    DeviationResult,
    ExplorerStats,
    MoveRecord,
)

router = APIRouter(prefix="/opening-deviation")


class ClassifyMoveRequest(BaseModel):
    position_fen: str
    next_move: str


class FindDeviationRequest(BaseModel):
    records: list[MoveRecord]


@router.get("/stats", response_model=ExplorerStats)
async def get_stats(fen: str) -> ExplorerStats:
    stats = await deps.get_service().get_stats(fen)

    if stats is None:
        raise HTTPException(status_code=404, detail="No Explorer data available for this position.")

    return stats


@router.post("/classify", response_model=ClassificationResult)
async def classify_move(request: ClassifyMoveRequest) -> ClassificationResult:
    return await deps.get_service().classify_move(request.position_fen, request.next_move)


@router.post("/find-deviation", response_model=DeviationResult)
async def find_first_deviation(request: FindDeviationRequest) -> DeviationResult:
    return await deps.get_service().find_first_deviation(request.records)
