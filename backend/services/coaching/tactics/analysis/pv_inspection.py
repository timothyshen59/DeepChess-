from __future__ import annotations

from collections.abc import Iterable

import chess

from ..schemas import PvFeature
from .board_state import material_for_color, safe_uci_move


def inspect_pv(
    board_before: chess.Board,
    pv_uci: Iterable[str],
) -> PvFeature:
    """Replay the legal prefix of a principal variation."""
    board = board_before.copy(stack=False)
    root_color = board.turn
    material_before = material_for_color(board, root_color)

    contains_check = False
    contains_capture = False
    contains_checkmate = False
    valid_prefix_length = 0
    invalid_move: str | None = None

    for move_uci in pv_uci:
        move = safe_uci_move(move_uci)

        if move is None or move not in board.legal_moves:
            invalid_move = move_uci
            break

        contains_check = contains_check or board.gives_check(move)
        contains_capture = contains_capture or board.is_capture(move)

        board.push(move)

        contains_checkmate = contains_checkmate or board.is_checkmate()
        valid_prefix_length += 1

    material_after = material_for_color(board, root_color)

    return PvFeature(
        valid_prefix_length=valid_prefix_length,
        contains_check=contains_check,
        contains_capture=contains_capture,
        contains_checkmate=contains_checkmate,
        material_swing_cp=material_after - material_before,
        invalid_move=invalid_move,
    )