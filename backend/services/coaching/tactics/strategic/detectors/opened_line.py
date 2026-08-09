from __future__ import annotations

import chess

from ..models import BoardDelta, LineDirection, OpenedLine, StrategicFact


class OpenedLineDetector:
    def detect(self, delta: BoardDelta) -> list[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        color = delta.moving_color
        facts: list[StrategicFact] = []

        for square, piece in after.piece_map().items():
            if piece.color != color:
                continue
            if piece.piece_type not in {chess.BISHOP, chess.ROOK, chess.QUEEN}:
                continue

            after_attacks = set(after.attacks(square))
            before_piece = before.piece_at(square)
            before_attacks = (
                set(before.attacks(square)) if before_piece == piece
                else set()
            )

            newly_controlled = after_attacks - before_attacks
            grouped: dict[LineDirection, list[chess.Square]] = {}

            for target_square in newly_controlled:
                direction = self._direction(square, target_square)
                if direction is None:
                    continue
                grouped.setdefault(direction, []).append(target_square)

            for direction, squares in grouped.items():
                facts.append(
                    OpenedLine(
                        piece_square=square,
                        piece_type=piece.piece_type,
                        direction=direction,
                        newly_controlled_squares=tuple(sorted(squares)),
                        moving_color=color,
                    )
                )

        return sorted(
            set(facts),
            key=lambda fact: (fact.piece_square, fact.direction.value),
        )

    def _direction(
        self,
        source: chess.Square,
        target: chess.Square,
    ) -> LineDirection | None:
        file_delta = chess.square_file(target) - chess.square_file(source)
        rank_delta = chess.square_rank(target) - chess.square_rank(source)

        if file_delta == 0 and rank_delta > 0:
            return LineDirection.NORTH
        if file_delta == 0 and rank_delta < 0:
            return LineDirection.SOUTH
        if rank_delta == 0 and file_delta > 0:
            return LineDirection.EAST
        if rank_delta == 0 and file_delta < 0:
            return LineDirection.WEST
        if file_delta > 0 and rank_delta > 0:
            return LineDirection.NORTH_EAST
        if file_delta < 0 and rank_delta > 0:
            return LineDirection.NORTH_WEST
        if file_delta > 0 and rank_delta < 0:
            return LineDirection.SOUTH_EAST
        if file_delta < 0 and rank_delta < 0:
            return LineDirection.SOUTH_WEST
        return None