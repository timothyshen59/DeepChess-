from __future__ import annotations

from dataclasses import dataclass

import chess

from ..models import BoardDelta, PieceSafety, StrategicFact


@dataclass(frozen=True)
class SafetyCounts:
    attackers: int
    defenders: int


class PieceSafetyDetector:
    def detect(self, delta: BoardDelta) -> list[StrategicFact]:
        before = delta.board_before
        after = delta.board_after

        color = delta.moving_color
        opponent = not color

        facts: list[StrategicFact] = []

        for square, piece in self._candidate_pieces(after, color):
            previous_square = self._previous_square(
                before=before,
                move=delta.best_move,
                current_square=square,
                piece=piece,
            )

            if previous_square is None:
                continue

            before_safety = self._safety(
                board=before,
                piece_color=color,
                enemy_color=opponent,
                square=previous_square,
            )

            after_safety = self._safety(
                board=after,
                piece_color=color,
                enemy_color=opponent,
                square=square,
            )

            if not self._safety_improved(before_safety, after_safety):
                continue

            facts.append(
                PieceSafety(
                    piece_square=square,
                    piece_type=piece.piece_type,
                    enemy_attackers_before=before_safety.attackers,
                    enemy_attackers_after=after_safety.attackers,
                    friendly_defenders_before=before_safety.defenders,
                    friendly_defenders_after=after_safety.defenders,
                    moving_color=color,
                )
            )

        return sorted(facts, key=lambda fact: fact.piece_square)

    @staticmethod
    def _candidate_pieces(
        board: chess.Board,
        color: chess.Color,
    ):
        """Friendly non-pawn, non-king pieces."""

        for square, piece in board.piece_map().items():
            if piece.color != color:
                continue

            if piece.piece_type in {chess.PAWN, chess.KING}:
                continue

            yield square, piece

    @staticmethod
    def _safety(
        board: chess.Board,
        piece_color: chess.Color,
        enemy_color: chess.Color,
        square: chess.Square,
    ) -> SafetyCounts:
        return SafetyCounts(
            attackers=len(board.attackers(enemy_color, square)),
            defenders=len(board.attackers(piece_color, square)),
        )

    @staticmethod
    def _safety_improved(
        before: SafetyCounts,
        after: SafetyCounts,
    ) -> bool:
        return (
            after.attackers < before.attackers
            or after.defenders > before.defenders
        )

    @staticmethod
    def _previous_square(
        before: chess.Board,
        move: chess.Move,
        current_square: chess.Square,
        piece: chess.Piece,
    ) -> chess.Square | None:
        """Returns where this piece was before the move."""

        if current_square == move.to_square:
            moved_piece = before.piece_at(move.from_square)

            if (
                moved_piece is not None
                and moved_piece.piece_type == piece.piece_type
            ):
                return move.from_square

        if before.piece_at(current_square) == piece:
            return current_square

        return None