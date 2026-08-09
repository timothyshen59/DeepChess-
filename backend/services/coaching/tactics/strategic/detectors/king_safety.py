from __future__ import annotations

import chess

from ..models import BoardDelta, ImprovedKingSafety, StrategicFact


class KingSafetyDetector:
    def detect(self, delta: BoardDelta) -> list[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        color = delta.moving_color
        opponent = not color

        before_king = before.king(color)
        after_king = after.king(color)

        if before_king is None or after_king is None:
            return []

        before_zone = self._king_zone(before_king)
        after_zone = self._king_zone(after_king)

        attacks_before = self._enemy_attacked_count(before, opponent, before_zone)
        attacks_after = self._enemy_attacked_count(after, opponent, after_zone)

        newly_defended = tuple(
            square
            for square in sorted(after_zone)
            if after.attackers(color, square) and not before.attackers(color, square)
        )

        if attacks_after >= attacks_before and not newly_defended:
            return []

        return [
            ImprovedKingSafety(
                king_square_before=before_king,
                king_square_after=after_king,
                enemy_attacked_zone_squares_before=attacks_before,
                enemy_attacked_zone_squares_after=attacks_after,
                newly_defended_zone_squares=newly_defended,
                moving_color=color,
            )
        ]

    def _king_zone(self, king_square: chess.Square) -> frozenset[chess.Square]:
        mask = chess.BB_KING_ATTACKS[king_square] | chess.BB_SQUARES[king_square]
        return frozenset(chess.scan_reversed(mask))

    def _enemy_attacked_count(
        self,
        board: chess.Board,
        enemy_color: chess.Color,
        squares: frozenset[chess.Square],
    ) -> int:
        return sum(bool(board.attackers(enemy_color, square)) for square in squares)
