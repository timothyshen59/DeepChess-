"""
Predict white and black player Elo from PGN game using transformers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.pgn_utils import InvalidPgnError, extract_moves
from services.transformer import predict_elo

router = APIRouter()

class PredictRequest(BaseModel):
    pgn: str

class PredictResponse(BaseModel):
    white_elo:         float
    black_elo:         float
    white_elo_rounded: int
    black_elo_rounded: int

@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    try:
        moves = extract_moves(request.pgn)
    except InvalidPgnError as error:
        raise HTTPException(status_code=400, detail="Invalid PGN") from error

    if not moves:
        raise HTTPException(status_code=400, detail="Game has no moves")

    white_elo, black_elo = predict_elo(moves)
 
    return PredictResponse(
        white_elo         = white_elo,
        black_elo         = black_elo,
        white_elo_rounded = round(white_elo / 50) * 50,
        black_elo_rounded = round(black_elo / 50) * 50,
    )
