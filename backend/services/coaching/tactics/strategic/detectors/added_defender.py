from __future__ import annotations

import chess

from ..models import AddedDefender, BoardDelta, StrategicFact


class AddedDefenderDetector:
    def detect(self, delta: BoardDelta) -> list[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        color = delta.moving_color
        facts: list[StrategicFact] = []

        for target_square, target_piece in after.piece_map().items():
            if target_piece.color != color or target_piece.piece_type == chess.KING:
                continue

            for defender_square in after.attackers(color, target_square):
                if defender_square == target_square:
                    continue

                defender_piece = after.piece_at(defender_square)
                if defender_piece is None:
                    continue

                defender_existed_before = (
                    before.piece_at(defender_square) == defender_piece
                    and defender_square in before.attackers(color, target_square)
                )

                if defender_existed_before:
                    continue

                facts.append(
                    AddedDefender(
                        defender_square=defender_square,
                        defender_piece_type=defender_piece.piece_type,
                        protected_square=target_square,
                        protected_piece_type=target_piece.piece_type,
                        moving_color=color,
                    )
                )

        return sorted(
            set(facts),
            key=lambda fact: (
                fact.protected_square,
                fact.defender_square,
                fact.defender_piece_type,
            ),
        )