from __future__ import annotations

from ..analysis.board_state import safe_board, safe_uci_move
from ..schemas import AnnotatedMove, InputIssue


def validate_moves(
    annotated_moves: list[AnnotatedMove],
) -> tuple[list[AnnotatedMove], list[InputIssue]]:
    """Validate annotations while retaining valid moves from the same game."""
    valid_moves: list[AnnotatedMove] = []
    issues: list[InputIssue] = []

    for annotated_move in annotated_moves:
        board = safe_board(annotated_move.fen_before)

        if board is None:
            issues.append(
                InputIssue(
                    ply=annotated_move.ply,
                    code="invalid_fen",
                    message=(
                        "fen_before is invalid; the move was excluded from tactical analysis."
                    ),
                )
            )
            continue

        if board.turn != (annotated_move.color == "white"):
            issues.append(
                InputIssue(
                    ply=annotated_move.ply,
                    code="color_turn_mismatch",
                    message=("Annotated color does not match the side to move in fen_before."),
                    severity="warning",
                )
            )

        played_move = safe_uci_move(annotated_move.played_uci)

        if played_move is None or played_move not in board.legal_moves:
            issues.append(
                InputIssue(
                    ply=annotated_move.ply,
                    code="illegal_played_move",
                    message=(
                        f"Played move '{annotated_move.played_uci}' is illegal "
                        "in fen_before; it was excluded from tactical analysis."
                    ),
                )
            )
            continue

        if annotated_move.best_move_uci:
            best_move = safe_uci_move(annotated_move.best_move_uci)

            if best_move is None or best_move not in board.legal_moves:
                issues.append(
                    InputIssue(
                        ply=annotated_move.ply,
                        code="illegal_best_move",
                        message=(
                            f"Best move '{annotated_move.best_move_uci}' is "
                            "illegal in fen_before; defensive analysis remains "
                            "available but best-line comparison is unavailable."
                        ),
                        severity="warning",
                    )
                )

        valid_moves.append(annotated_move)

    return valid_moves, issues
