"""
Shared PGN parsing helpers.

routes/analyze.py, routes/predict.py, and the tactics test pipeline each used
to hand-roll their own PGN-to-moves extraction. This module is the single
place that walks a PGN's mainline and produces per-move dicts, so new
consumers (the opening agent) don't add a fourth copy.
"""

from __future__ import annotations

from io import StringIO

import chess
import chess.pgn


class InvalidPgnError(ValueError):
    """The supplied PGN text could not be parsed into a game."""


def read_game(pgn_text: str) -> chess.pgn.Game:
    """Parse PGN text into a `chess.pgn.Game`, raising on invalid input."""
    game = chess.pgn.read_game(StringIO(pgn_text.strip()))

    if game is None or game.errors:
        raise InvalidPgnError("Invalid PGN. Check the notation and try again.")

    return game


def extract_moves(pgn_text: str) -> list[dict]:
    """Walk a PGN's mainline into per-move dicts.

    Each dict carries `move_number`, `color`, `move_san`, `move_uci`,
    `fen_before`, and `fen_after` — the superset of fields the existing
    `/analyze` and `/predict` routes each needed individually.
    """
    game = read_game(pgn_text)
    board = game.board()
    moves: list[dict] = []

    for move_number, move in enumerate(game.mainline_moves(), start=1):
        fen_before = board.fen()
        san = board.san(move)
        color = "white" if board.turn == chess.WHITE else "black"

        board.push(move)

        moves.append({
            "move_number": move_number,
            "move_san": san,
            "move_uci": move.uci(),
            "fen_before": fen_before,
            "fen_after": board.fen(),
            "color": color,
        })

    return moves
