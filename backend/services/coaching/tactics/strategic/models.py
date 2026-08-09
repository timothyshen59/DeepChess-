from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import chess


class StrategicFactKind(StrEnum):
    ADDED_DEFENDER = "added_defender"
    REMOVED_DEFENDER = "removed_defender"
    OPENED_LINE = "opened_line"
    DEVELOPED_PIECE = "developed_piece"
    ACTIVATED_PIECE = "activated_piece"
    IMPROVED_KING_SAFETY = "improved_king_safety"
    PIECE_SAFETY = "piece_safety"
    PIN_RELIEF = "pin_relief"


class LineDirection(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTH_EAST = "north_east"
    NORTH_WEST = "north_west"
    SOUTH_EAST = "south_east"
    SOUTH_WEST = "south_west"


@dataclass(frozen=True, slots=True)
class BoardDelta:
    before_fen: str
    after_fen: str
    best_move_uci: str
    moving_color: chess.Color

    @classmethod
    def from_boards(
        cls,
        board_before: chess.Board,
        board_after: chess.Board,
        best_move: chess.Move,
    ) -> BoardDelta:
        if best_move not in board_before.legal_moves:
            raise ValueError("best_move must be legal in board_before")

        expected_after = board_before.copy(stack=False)
        expected_after.push(best_move)

        if (
            expected_after.board_fen() != board_after.board_fen()
            or expected_after.turn != board_after.turn
            or expected_after.castling_rights != board_after.castling_rights
            or expected_after.ep_square != board_after.ep_square
        ):
            raise ValueError("board_after must equal board_before after best_move")

        return cls(
            before_fen=board_before.fen(en_passant="fen"),
            after_fen=board_after.fen(en_passant="fen"),
            best_move_uci=best_move.uci(),
            moving_color=board_before.turn,
        )

    @property
    def board_before(self) -> chess.Board:
        return chess.Board(self.before_fen)

    @property
    def board_after(self) -> chess.Board:
        return chess.Board(self.after_fen)

    @property
    def best_move(self) -> chess.Move:
        return chess.Move.from_uci(self.best_move_uci)


@dataclass(frozen=True, slots=True)
class AddedDefender:
    defender_square: chess.Square
    defender_piece_type: chess.PieceType
    protected_square: chess.Square
    protected_piece_type: chess.PieceType
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.ADDED_DEFENDER


@dataclass(frozen=True, slots=True)
class RemovedDefender:
    removed_defender_square: chess.Square
    removed_defender_piece_type: chess.PieceType
    target_square: chess.Square
    target_piece_type: chess.PieceType
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.REMOVED_DEFENDER


@dataclass(frozen=True, slots=True)
class OpenedLine:
    piece_square: chess.Square
    piece_type: chess.PieceType
    direction: LineDirection
    newly_controlled_squares: tuple[chess.Square, ...]
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.OPENED_LINE


@dataclass(frozen=True, slots=True)
class DevelopedPiece:
    piece_type: chess.PieceType
    from_square: chess.Square
    to_square: chess.Square
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.DEVELOPED_PIECE


@dataclass(frozen=True, slots=True)
class ActivatedPiece:
    piece_square: chess.Square
    piece_type: chess.PieceType
    controlled_squares_before: int
    controlled_squares_after: int
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.ACTIVATED_PIECE


@dataclass(frozen=True, slots=True)
class ImprovedKingSafety:
    king_square_before: chess.Square
    king_square_after: chess.Square
    enemy_attacked_zone_squares_before: int
    enemy_attacked_zone_squares_after: int
    newly_defended_zone_squares: tuple[chess.Square, ...]
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.IMPROVED_KING_SAFETY


@dataclass(frozen=True, slots=True)
class PieceSafety:
    piece_square: chess.Square
    piece_type: chess.PieceType
    enemy_attackers_before: int
    enemy_attackers_after: int
    friendly_defenders_before: int
    friendly_defenders_after: int
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.PIECE_SAFETY


@dataclass(frozen=True, slots=True)
class PinRelief:
    piece_type: chess.PieceType
    piece_square_before: chess.Square
    piece_square_after: chess.Square
    king_square: chess.Square
    moving_color: chess.Color

    @property
    def kind(self) -> StrategicFactKind:
        return StrategicFactKind.PIN_RELIEF


StrategicFact = (
    AddedDefender
    | RemovedDefender
    | OpenedLine
    | DevelopedPiece
    | ActivatedPiece
    | ImprovedKingSafety
    | PieceSafety
    | PinRelief
)


@dataclass(frozen=True, slots=True)
class StrategicExplanation:
    facts: tuple[StrategicFact, ...]


def fact_importance(fact: StrategicFact) -> int:
    if isinstance(fact, ImprovedKingSafety):
        return 100
    if isinstance(fact, PinRelief):
        return 95
    if isinstance(fact, RemovedDefender):
        return 90
    if isinstance(fact, PieceSafety):
        return 85
    if isinstance(fact, AddedDefender):
        return 80 if fact.protected_piece_type >= chess.ROOK else 65
    if isinstance(fact, OpenedLine):
        return 75
    if isinstance(fact, ActivatedPiece):
        return 50
    return 40


def fact_sort_key(fact: StrategicFact) -> tuple[int, str, str]:
    return (-fact_importance(fact), fact.kind.value, repr(fact))
