from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

import chess


PIECE_VALUES_CP: Mapping[chess.PieceType, int] = MappingProxyType(
    {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20_000,
    }
)


def piece_name(piece: chess.Piece | None) -> str | None:
    """Return a human-readable piece name."""
    return chess.piece_name(piece.piece_type) if piece else None


def material_for_color(board: chess.Board, color: chess.Color) -> int:
    """Return total remaining material for one color in centipawns."""
    return sum(
        PIECE_VALUES_CP[piece.piece_type]
        for piece in board.piece_map().values()
        if piece.color == color
    )


def safe_board(fen: str) -> chess.Board | None:
    """Parse a FEN without allowing malformed external input to raise."""
    try:
        return chess.Board(fen)
    except (TypeError, ValueError):
        return None


def safe_uci_move(move_uci: str | None) -> chess.Move | None:
    """Parse UCI without allowing malformed external input to raise."""
    if not move_uci:
        return None

    try:
        return chess.Move.from_uci(move_uci)
    except (TypeError, ValueError):
        return None