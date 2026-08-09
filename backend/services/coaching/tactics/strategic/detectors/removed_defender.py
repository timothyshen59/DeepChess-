from __future__ import annotations

from collections.abc import Sequence

import chess

from ..models import BoardDelta, RemovedDefender, StrategicFact


class RemovedDefenderDetector:
    def detect(self, delta: BoardDelta) -> Sequence[StrategicFact]:
        before = delta.board_before
        after = delta.board_after

        mover = delta.moving_color
        opponent = not mover

        facts: set[RemovedDefender] = set()

        for target_square in self._candidate_targets(before, after, opponent):
            facts.update(
                self._removed_defenders(
                    before=before,
                    after=after,
                    target_square=target_square,
                    moving_color=mover,
                    defending_color=opponent,
                )
            )

        return sorted(
            facts,
            key=lambda fact: (
                fact.target_square,
                fact.removed_defender_square,
                fact.removed_defender_piece_type,
            ),
        )

    def _candidate_targets(
        self,
        before: chess.Board,
        after: chess.Board,
        defending_color: chess.Color,
    ) -> list[chess.Square]:
        """Pieces that survived the move and may have lost defenders."""

        targets: list[chess.Square] = []

        for square, piece in after.piece_map().items():
            if piece.color != defending_color:
                continue

            if piece.piece_type == chess.KING:
                continue

            if before.piece_at(square) != piece:
                continue

            targets.append(square)

        return targets

    def _removed_defenders(
        self,
        *,
        before: chess.Board,
        after: chess.Board,
        target_square: chess.Square,
        moving_color: chess.Color,
        defending_color: chess.Color,
    ) -> list[RemovedDefender]:
        """Find defenders of a target that disappeared or stopped defending."""

        target_piece = after.piece_at(target_square)
        assert target_piece is not None

        facts: list[RemovedDefender] = []

        for defender_square in before.attackers(defending_color, target_square):
            if defender_square == target_square:
                continue

            defender_before = before.piece_at(defender_square)
            if defender_before is None:
                continue

            if self._still_defends(
                before=before,
                after=after,
                defender_square=defender_square,
                target_square=target_square,
                defending_color=defending_color,
                defender_before=defender_before,
            ):
                continue

            facts.append(
                RemovedDefender(
                    removed_defender_square=defender_square,
                    removed_defender_piece_type=defender_before.piece_type,
                    target_square=target_square,
                    target_piece_type=target_piece.piece_type,
                    moving_color=moving_color,
                )
            )

        return facts

    @staticmethod
    def _still_defends(
        *,
        before: chess.Board,
        after: chess.Board,
        defender_square: chess.Square,
        target_square: chess.Square,
        defending_color: chess.Color,
        defender_before: chess.Piece,
    ) -> bool:
        """Returns True if the same defender still protects the target."""

        defender_after = after.piece_at(defender_square)

        if defender_after != defender_before:
            return False

        return defender_square in after.attackers(
            defending_color,
            target_square,
        )
