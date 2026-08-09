"""
Annotates each move in PGN wiht Stockfish eval.
Returns cp_loss, quality_label, and color per move

"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.pgn_utils import InvalidPgnError, extract_moves
from services.stockfish import annotate_moves

router = APIRouter()


class AnalyzeRequest(BaseModel):
    pgn: str


class MoveAnnotation(BaseModel):
    move_number: int
    color: str
    move_san: str
    move_uci: str
    cp_loss: float | None
    quality: str
    color_hex: str
    principal_variation: list[str]


class AnalyzeResponse(BaseModel):
    moves: list[MoveAnnotation]
    avg_white_cp_loss: float | None
    avg_black_cp_loss: float | None
    failed_positions: int
    total_positions: int
    is_partial: bool


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    try:
        moves = extract_moves(request.pgn)
    except InvalidPgnError as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid PGN. Check the notation and try again.",
        ) from error

    analysis = annotate_moves(moves)
    annotated = analysis["moves"]

    white_losses = [
        move["cp_loss"]
        for i, move in enumerate(annotated)
        if i % 2 == 0 and move["cp_loss"] is not None
    ]

    black_losses = [
        move["cp_loss"]
        for i, move in enumerate(annotated)
        if i % 2 == 1 and move["cp_loss"] is not None
    ]

    avg_black_cp_loss = sum(black_losses) / len(black_losses) if black_losses else None
    avg_white_cp_loss = sum(white_losses) / len(white_losses) if white_losses else None

    return AnalyzeResponse(
        moves=[MoveAnnotation(**move) for move in annotated],
        avg_black_cp_loss=avg_black_cp_loss,
        avg_white_cp_loss=avg_white_cp_loss,
        failed_positions=analysis["failed_positions"],
        total_positions=analysis["total_positions"],
        is_partial=analysis["is_partial"],
    )
