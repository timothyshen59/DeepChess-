from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ColorName = Literal["white", "black"]
Confidence = Literal["high", "medium", "low"]
MoveQuality = Literal["good", "inaccuracy", "mistake", "blunder", "unknown"]
TacticalCategory = Literal["offensive", "defensive", "mixed"]

TacticalMotif = Literal[
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "deflection",
    "overload",
    "removal_of_defender",
    "back_rank",
    "hanging_piece",
    "mate_threat",
    "zwischenzug",
    "missed_check",
    "missed_capture",
    "missed_defense",
    "king_safety",
    "calculation_error",
    "other",
]


class AnnotatedMove(BaseModel):
    """Engine annotation for one played move.

    The model deliberately permits malformed UCI/FEN strings at ingestion time.
    The graph records them as input issues instead of failing the entire game.
    """

    ply: int = Field(ge=1)
    move_number: int = Field(ge=1)
    color: ColorName

    cp_loss: int = Field(default=0, ge=0)
    quality: str

    fen_before: str = Field(min_length=1)
    played_san: str = Field(default="?")
    played_uci: str = Field(min_length=1)

    best_move_san: str | None = None
    best_move_uci: str | None = None

    principal_variation_uci: list[str] = Field(default_factory=list)
    principal_variation_san: list[str] = Field(default_factory=list)

    mate_in_plies: int | None = Field(default=None, ge=1)
    depth: int | None = Field(default=None, ge=1)


class InputIssue(BaseModel):
    ply: int | None = None
    code: str
    message: str
    severity: Literal["warning", "error"] = "error"


class KingSafetyFeature(BaseModel):
    is_in_check: bool
    king_square: str | None
    legal_king_moves: int
    enemy_attackers_of_king: int
    opponent_has_mate_in_one: bool


class MoveFeature(BaseModel):
    move_uci: str | None
    is_legal: bool
    is_check: bool = False
    is_capture: bool = False
    is_promotion: bool = False

    gives_checkmate: bool = False
    captured_piece: str | None = None
    resulting_king_safety: KingSafetyFeature | None = None
    error: str | None = None


class HangingPieceFeature(BaseModel):
    square: str
    piece: str
    piece_value_cp: int
    attackers: int
    defenders: int
    can_be_captured_immediately: bool


class DefensiveFeature(BaseModel):
    opponent_has_forcing_check: bool
    opponent_has_mate_in_one: bool
    immediate_capture_targets: list[HangingPieceFeature] = Field(default_factory=list)
    largest_immediate_capture_cp: int = 0
    exposed_own_pieces: list[HangingPieceFeature] = Field(default_factory=list)


class PvFeature(BaseModel):
    valid_prefix_length: int
    contains_check: bool
    contains_capture: bool
    contains_checkmate: bool
    material_swing_cp: int
    invalid_move: str | None = None


class CandidateFeatures(BaseModel):
    best_move: MoveFeature | None = None
    played_move: MoveFeature | None = None
    played_defense: DefensiveFeature | None = None
    principal_variation: PvFeature | None = None


class TacticalCandidate(BaseModel):
    ply: int
    move_number: int
    player_color: ColorName
    fen_before: str
    played_san: str
    played_uci: str
    best_move_san: str | None = None
    best_move_uci: str | None = None
    principal_variation_uci: list[str] = Field(default_factory=list)

    cp_loss: int
    quality: MoveQuality
    mate_in_plies: int | None = None
    depth: int | None = None


class TacticalLesson(BaseModel):
    ply: int
    move_number: int
    player_color: ColorName
    category: TacticalCategory
    motif: TacticalMotif
    played_move: str
    better_move: str | None = None
    cp_loss: int = Field(ge=0)
    explanation: str = Field(min_length=1, max_length=700)
    calculation_habit: str = Field(min_length=1, max_length=350)
    confidence: Confidence


class TacticsReport(BaseModel):
    headline: str = Field(min_length=1, max_length=160)
    recurring_pattern: str = Field(min_length=1, max_length=500)
    crucial_mistakes: list[TacticalLesson] = Field(default_factory=list, max_length=4)
    input_issues: list[InputIssue] = Field(default_factory=list)
