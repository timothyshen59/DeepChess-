from __future__ import annotations

import chess

from ..schemas import MoveFeature
from .board_state import piece_name, safe_uci_move
from .king_safety import king_safety


def move_feature(board: chess.Board, move_uci: str | None) -> MoveFeature:
    """Extract verified board facts for a candidate move."""
    move = safe_uci_move(move_uci)

    if move is None:
        return MoveFeature(
            move_uci=move_uci,
            is_legal=False,
            error="Move is missing or is not valid UCI.",
        )

    if move not in board.legal_moves:
        return MoveFeature(
            move_uci=move_uci,
            is_legal=False,
            error="Move is not legal in fen_before.",
        )

    captured_piece = board.piece_at(move.to_square)
    if board.is_en_passant(move):
        captured_piece = chess.Piece(chess.PAWN, not board.turn)

    is_check = board.gives_check(move)
    is_capture = board.is_capture(move)

    board_after = board.copy(stack=False)
    board_after.push(move)

    return MoveFeature(
        move_uci=move_uci,
        is_legal=True,
        is_check=is_check,
        is_capture=is_capture,
        is_promotion=move.promotion is not None,
        gives_checkmate=board_after.is_checkmate(),
        captured_piece=piece_name(captured_piece),
        resulting_king_safety=king_safety(
            board=board_after,
            color=not board_after.turn,
        ),
    )