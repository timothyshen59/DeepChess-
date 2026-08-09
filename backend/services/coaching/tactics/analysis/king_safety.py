from __future__ import annotations

import chess

from ..schemas import KingSafetyFeature


def has_mate_in_one(board: chess.Board) -> bool:
    """Return whether the current side to move has a legal mate in one."""
    for move in board.legal_moves:
        if not board.gives_check(move):
            continue

        board.push(move)
        is_mate = board.is_checkmate()
        board.pop()

        if is_mate:
            return True

    return False


def king_safety(
    board: chess.Board,
    color: chess.Color,
) -> KingSafetyFeature:
    """Extract king safety features without mutating the caller's board."""
    king_square = board.king(color)

    if king_square is None:
        return KingSafetyFeature(
            is_in_check=False,
            king_square=None,
            legal_king_moves=0,
            enemy_attackers_of_king=0,
            opponent_has_mate_in_one=False,
        )

    enemy = not color
    attackers = board.attackers(enemy, king_square)
    legal_king_moves = sum(
        1
        for move in board.legal_moves
        if move.from_square == king_square
    )

    return KingSafetyFeature(
        is_in_check=(
            board.is_check()
            if board.turn == color
            else board.is_attacked_by(enemy, king_square)
        ),
        king_square=chess.square_name(king_square),
        legal_king_moves=legal_king_moves,
        enemy_attackers_of_king=len(attackers),
        opponent_has_mate_in_one=has_mate_in_one(board),
    )