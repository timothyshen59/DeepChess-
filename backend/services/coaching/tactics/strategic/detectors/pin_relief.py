from __future__ import annotations

from collections.abc import Sequence

import chess

from ..models import BoardDelta, PinRelief, StrategicFact


class PinReliefDetector:
    def detect(self, delta: BoardDelta) -> Sequence[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        move = delta.best_move
        color = delta.moving_color
        king_square = after.king(color)

        if king_square is None:
            return []

        facts: list[PinRelief] = []

        for before_square, piece_before in before.piece_map().items():
            if piece_before.color != color or piece_before.piece_type == chess.KING:
                continue
            if not before.is_pinned(color, before_square):
                continue

            after_square = self._after_square(
                after=after,
                move=move,
                before_square=before_square,
                piece_before=piece_before,
            )

            if after_square is None or after.is_pinned(color, after_square):
                continue

            facts.append(
                PinRelief(
                    piece_type=piece_before.piece_type,
                    piece_square_before=before_square,
                    piece_square_after=after_square,
                    king_square=king_square,
                    moving_color=color,
                )
            )

        # Explicit intermediate annotation -- see added_defender.py's
        # detect() for why.
        sorted_facts: list[PinRelief] = sorted(
            set(facts), key=lambda fact: fact.piece_square_before
        )
        return sorted_facts

    def _after_square(
        self,
        after: chess.Board,
        move: chess.Move,
        before_square: chess.Square,
        piece_before: chess.Piece,
    ) -> chess.Square | None:
        candidate_square = move.to_square if before_square == move.from_square else before_square
        piece_after = after.piece_at(candidate_square)

        if piece_after == piece_before:
            return candidate_square

        return None
