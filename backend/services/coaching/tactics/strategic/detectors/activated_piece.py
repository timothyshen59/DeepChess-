from __future__ import annotations

from collections.abc import Sequence

import chess

from ..models import ActivatedPiece, BoardDelta, StrategicFact


class ActivatedPieceDetector:
    def detect(self, delta: BoardDelta) -> Sequence[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        move = delta.best_move
        color = delta.moving_color
        facts: list[ActivatedPiece] = []

        for after_square, piece_after in after.piece_map().items():
            if piece_after.color != color:
                continue
            if piece_after.piece_type not in {
                chess.KNIGHT,
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN,
            }:
                continue

            before_square = self._before_square(
                before=before,
                move=move,
                after_square=after_square,
                piece_after=piece_after,
            )

            if before_square is None:
                continue

            before_count = len(before.attacks(before_square))
            after_count = len(after.attacks(after_square))
            threshold = self._threshold(piece_after.piece_type)

            if after_count - before_count < threshold:
                continue

            facts.append(
                ActivatedPiece(
                    piece_square=after_square,
                    piece_type=piece_after.piece_type,
                    controlled_squares_before=before_count,
                    controlled_squares_after=after_count,
                    moving_color=color,
                )
            )

        # Explicit intermediate annotation -- see added_defender.py's
        # detect() for why (mypy's bidirectional inference otherwise solves
        # sorted()'s type parameter against the wider Sequence[StrategicFact]
        # return context instead of `facts`'s actual element type).
        sorted_facts: list[ActivatedPiece] = sorted(set(facts), key=lambda fact: fact.piece_square)
        return sorted_facts

    def _before_square(
        self,
        before: chess.Board,
        move: chess.Move,
        after_square: chess.Square,
        piece_after: chess.Piece,
    ) -> chess.Square | None:
        if after_square == move.to_square:
            moving_piece = before.piece_at(move.from_square)
            if moving_piece is not None and moving_piece.piece_type == piece_after.piece_type:
                return move.from_square

        if before.piece_at(after_square) == piece_after:
            return after_square

        return None

    def _threshold(self, piece_type: chess.PieceType) -> int:
        if piece_type == chess.KNIGHT:
            return 2
        return 3
