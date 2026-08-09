from __future__ import annotations

from collections.abc import Sequence

import chess

from ..models import AddedDefender, BoardDelta, StrategicFact


class AddedDefenderDetector:
    def detect(self, delta: BoardDelta) -> Sequence[StrategicFact]:
        before = delta.board_before
        after = delta.board_after
        color = delta.moving_color
        facts: list[AddedDefender] = []

        for target_square, target_piece in after.piece_map().items():
            if target_piece.color != color or target_piece.piece_type == chess.KING:
                continue

            for defender_square in after.attackers(color, target_square):
                if defender_square == target_square:
                    continue

                defender_piece = after.piece_at(defender_square)
                if defender_piece is None:
                    continue

                defender_existed_before = before.piece_at(
                    defender_square
                ) == defender_piece and defender_square in before.attackers(color, target_square)

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

        # Explicit intermediate annotation: without it, mypy's bidirectional
        # inference solves sorted()'s type parameter against detect()'s
        # wider `list[StrategicFact]` return context instead of `facts`'s
        # actual `list[AddedDefender]` element type, and the lambda's `fact`
        # ends up typed as the full 8-member Union.
        sorted_facts: list[AddedDefender] = sorted(
            set(facts),
            key=lambda fact: (
                fact.protected_square,
                fact.defender_square,
                fact.defender_piece_type,
            ),
        )
        return sorted_facts
