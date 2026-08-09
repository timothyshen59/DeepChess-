"""
The public coaching pipeline: PGN -> Stockfish annotation -> opening agent
-> tactics agent -> coordinator.

Nothing outside test code wired opening, tactics, and the coordinator
together before this module existed -- each feature only had its own
graph.py. This is pure sequencing of already-existing, already-tested
pieces; no new analysis, no agent business logic.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from services.coaching.coordinator.graph import build_coordinator_graph
from services.coaching.coordinator.schemas import CoordinatedReport
from services.coaching.opening.graph import OpeningDeps, build_opening_graph
from services.coaching.opening.schemas import OpeningReport
from services.coaching.tactics.graph import build_tactics_graph
from services.coaching.tactics.schemas import AnnotatedMove, TacticsReport
from services.pgn_utils import extract_moves
from services.stockfish import annotate_moves


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """All three real reports, not just the final one.

    `CoordinatedReport.opening_summary` deliberately doesn't carry
    `critical_mistakes` (see coordinator/schemas.py::OpeningSummary), so
    callers that need opening- or tactics-specific fields the coordinator
    doesn't pass through 1:1 need the originals directly.
    """

    coordinated: CoordinatedReport
    opening: OpeningReport
    tactics: TacticsReport


async def run_coaching_pipeline(pgn_text: str, opening_deps: OpeningDeps) -> PipelineResult:
    """Run the full coaching pipeline once for one PGN.

    `opening_deps` is an explicit parameter, same DI pattern
    `build_opening_graph` already uses -- production callers pass
    `services.coaching.opening.opening_deps.get_deps()`; tests pass a
    fixture-backed `OpeningDeps` pointing at a fake deviation-engine
    service (see services/coaching/opening/tests/fixtures/).
    """
    tactics_report = run_tactics(pgn_text)

    opening_graph = build_opening_graph(opening_deps)
    opening_result = await opening_graph.ainvoke(
        {
            "pgn": pgn_text,
            "fen": None,
            "user_color": None,
        }
    )
    opening_report = opening_result["report"]

    coordinator_graph = build_coordinator_graph()
    coordinator_result = coordinator_graph.invoke(
        {
            "opening_report": opening_report,
            "tactics_report": tactics_report,
        }
    )

    return PipelineResult(
        coordinated=coordinator_result["report"],
        opening=opening_report,
        tactics=tactics_report,
    )


def run_tactics(pgn_text: str) -> TacticsReport:
    """The tactics half of the pipeline, fed by the same production
    services.stockfish.annotate_moves() the /analyze route uses."""
    moves = extract_moves(pgn_text)
    analysis = annotate_moves(moves)
    annotated_moves = [_to_annotated_move(move) for move in analysis["moves"]]

    tactics_graph = build_tactics_graph()
    result = tactics_graph.invoke({"annotated_moves": annotated_moves})
    return result["report"]


def _to_annotated_move(move: dict) -> AnnotatedMove:
    """annotate_moves()'s dict shape -> AnnotatedMove.

    `move["move_number"]` from services/pgn_utils.py is actually a
    1-indexed ply counter (see that module's docstring) -- mirrors the
    same ply/move_number derivation used in
    services/coaching/opening/node.py.
    """
    ply = move["move_number"]

    return AnnotatedMove(
        ply=ply,
        move_number=(ply + 1) // 2,
        color=move["color"],
        cp_loss=move["cp_loss"] if move["cp_loss"] is not None else 0,
        quality=move["quality"],
        fen_before=move["fen_before"],
        played_san=move["move_san"],
        played_uci=move["move_uci"],
        best_move_uci=move.get("best_move_uci"),
        best_move_san=_uci_to_san(move["fen_before"], move.get("best_move_uci")),
        principal_variation_uci=move.get("principal_variation") or [],
    )


def _uci_to_san(fen_before: str, move_uci: str | None) -> str | None:
    if not move_uci:
        return None

    try:
        board = chess.Board(fen_before)
        move = chess.Move.from_uci(move_uci)
    except (TypeError, ValueError):
        return None

    if move not in board.legal_moves:
        return None

    return board.san(move)
