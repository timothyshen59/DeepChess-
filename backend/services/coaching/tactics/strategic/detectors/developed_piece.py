from __future__ import annotations

import chess

from ..models import BoardDelta, DevelopedPiece, StrategicFact


class DevelopedPieceDetector:
    """Detects when a knight or bishop is developed from its starting square."""

    def detect(self, delta: BoardDelta) -> list[StrategicFact]:
        board = delta.board_before
        move = delta.best_move

        piece = board.piece_at(move.from_square)
        if piece is None:
            return []

        if piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
            return []

        if move.from_square not in self._starting_squares(piece.color, piece.piece_type):
            return []

        return [
            DevelopedPiece(
                piece_type=piece.piece_type,
                from_square=move.from_square,
                to_square=move.to_square,
                moving_color=piece.color,
            )
        ]

    @staticmethod
    def _starting_squares(
        color: chess.Color,
        piece_type: chess.PieceType,
    ) -> set[chess.Square]:
        """Returns the starting squares for a knight or bishop."""

        if color == chess.WHITE:
            if piece_type == chess.KNIGHT:
                return {chess.B1, chess.G1}
            return {chess.C1, chess.F1}

        if piece_type == chess.KNIGHT:
            return {chess.B8, chess.G8}
        return {chess.C8, chess.F8}