from __future__ import annotations

import chess

from ..schemas import DefensiveFeature, HangingPieceFeature
from .board_state import PIECE_VALUES_CP, safe_uci_move
from .king_safety import has_mate_in_one


def _hanging_piece(
    board: chess.Board,
    square: chess.Square,
    defending_color: chess.Color,
) -> HangingPieceFeature | None:
    piece = board.piece_at(square)

    if piece is None or piece.color != defending_color:
        return None

    attacker_count = len(board.attackers(not defending_color, square))
    if attacker_count == 0:
        return None

    can_be_captured = any(
        move.to_square == square and board.is_capture(move) for move in board.legal_moves
    )

    return HangingPieceFeature(
        square=chess.square_name(square),
        piece=chess.piece_name(piece.piece_type),
        piece_value_cp=PIECE_VALUES_CP[piece.piece_type],
        attackers=attacker_count,
        defenders=len(board.attackers(defending_color, square)),
        can_be_captured_immediately=can_be_captured,
    )


def _immediate_capture_targets(
    board: chess.Board,
    defending_color: chess.Color,
) -> list[HangingPieceFeature]:
    targets: list[HangingPieceFeature] = []
    seen_squares: set[chess.Square] = set()

    for reply in board.legal_moves:
        if not board.is_capture(reply) or reply.to_square in seen_squares:
            continue

        target = _hanging_piece(
            board=board,
            square=reply.to_square,
            defending_color=defending_color,
        )

        if target is not None:
            targets.append(target)
            seen_squares.add(reply.to_square)

    return sorted(
        targets,
        key=lambda item: item.piece_value_cp,
        reverse=True,
    )


def _exposed_pieces(
    board: chess.Board,
    defending_color: chess.Color,
) -> list[HangingPieceFeature]:
    exposed = [
        feature
        for square, piece in board.piece_map().items()
        if piece.color == defending_color
        if (
            feature := _hanging_piece(
                board=board,
                square=square,
                defending_color=defending_color,
            )
        )
        is not None
    ]

    return sorted(
        exposed,
        key=lambda item: (
            item.can_be_captured_immediately,
            item.piece_value_cp,
        ),
        reverse=True,
    )


def defensive_feature(
    board_before: chess.Board,
    played_uci: str,
) -> DefensiveFeature | None:
    """Find immediate tactical threats enabled by a played move."""
    move = safe_uci_move(played_uci)

    if move is None or move not in board_before.legal_moves:
        return None

    player_color = board_before.turn
    board_after = board_before.copy(stack=False)
    board_after.push(move)

    capture_targets = _immediate_capture_targets(
        board=board_after,
        defending_color=player_color,
    )

    return DefensiveFeature(
        opponent_has_forcing_check=any(
            board_after.gives_check(reply) for reply in board_after.legal_moves
        ),
        opponent_has_mate_in_one=has_mate_in_one(board_after),
        immediate_capture_targets=capture_targets,
        largest_immediate_capture_cp=max(
            (target.piece_value_cp for target in capture_targets),
            default=0,
        ),
        exposed_own_pieces=_exposed_pieces(
            board=board_after,
            defending_color=player_color,
        ),
    )
