from __future__ import annotations

import chess

from services.opening_deviation.deviation.service import OpeningDeviationService
from services.pgn_utils import InvalidPgnError, extract_moves
from services.stockfish import aannotate_moves

from .eco.eco_index import EcoIndex
from .games.model_games import get_model_games
from .report.mistake_builder import build_critical_mistake
from .report.report_builder import build_report
from .report.strategic_context import get_strategic_context
from .schemas import (
    CriticalMistake,
    Deviation,
    InputIssue,
    OpeningIdentity,
)
from .state import OpeningState

MISTAKE_SEVERITIES = frozenset({"mistake", "blunder"})
MAX_BETTER_LINE_EXTRA_PLIES = 4


def parse_input(state: OpeningState) -> dict:
    """Validate the PGN and extract its move list.

    Reuses services/pgn_utils.py rather than adding a fourth hand-rolled
    PGN-to-moves extractor (routes/analyze.py and routes/predict.py already
    had their own copies before this feature).
    """
    try:
        moves = extract_moves(state["pgn"])
    except InvalidPgnError as error:
        return {
            "moves": [],
            "input_issues": [InputIssue(code="invalid_pgn", message=str(error))],
        }

    if not moves:
        # python-chess's PGN parser is lenient -- text with no real movetext
        # (or headers only) parses as a valid, empty game rather than
        # raising. Flag it explicitly rather than silently reporting an
        # empty, unidentifiable opening.
        return {
            "moves": [],
            "input_issues": [
                InputIssue(
                    code="no_moves",
                    message="The PGN parsed without any moves; there is nothing to analyze.",
                )
            ],
        }

    return {"moves": moves, "input_issues": []}


def identify_opening(state: OpeningState, eco_index: EcoIndex) -> dict:
    """ECO-tree longest-prefix match -> opening name/ECO/variation."""
    moves_uci = [move["move_uci"] for move in state.get("moves", [])]
    entry, matched_plies = eco_index.identify(moves_uci)

    if entry is None:
        return {"opening": OpeningIdentity()}

    return {
        "opening": OpeningIdentity(
            eco=entry.eco,
            name=entry.name,
            variation=entry.variation,
            matched_plies=matched_plies,
        )
    }


async def compute_deviation(
    state: OpeningState,
    deviation_service: OpeningDeviationService,
    max_plies: int,
) -> dict:
    """Walk the opening-phase moves ply by ply, classifying each against
    the Lichess Explorer engine (services/opening_deviation/), and stop at
    the first real deviation -- then extend it into a multi-move better
    line.

    Mirrors the control flow of the old Polyglot-based `find_deviation`
    (a ply with too little sample data ends the walk rather than being
    silently skipped, so a game that outruns the engine's coverage is
    reported as `book_unavailable`/`followed_theory` correctly, never as a
    false "deviation" or a false "followed theory the whole way"), just
    sourcing each ply's classification live instead of from a static book.
    """
    moves = state.get("moves", [])[:max_plies]

    if not moves:
        return {
            "deviation": Deviation(
                status="insufficient_moves",
                note="The game had no moves to compare against theory.",
            )
        }

    covered_plies = 0

    for move in moves:
        result = await deviation_service.classify_move(move["fen_before"], move["move_uci"])

        if result.classification == "OUT_OF_BOOK":
            # Not enough real data at this position to confidently call it
            # anything -- stop rather than report a falsely-confident result.
            break

        covered_plies += 1

        if result.classification == "DEVIATION":
            ply = move["move_number"]
            better = result.best_move

            deviation = Deviation(
                status="deviated",
                ply=ply,
                move_number=(ply + 1) // 2,
                player_color=move["color"],
                played_san=move["move_san"] or move["move_uci"],
                better_move_san=better.san if better else None,
                better_move_uci=better.uci if better else None,
                played_move_share=result.played_move_share,
                theory_tier=result.classification,
                note=f"Left known theory on move {(ply + 1) // 2} ({move['color']}).",
            )

            if deviation.better_move_uci:
                deviation = await _extend_better_line(state, deviation, deviation_service)

            return {"deviation": deviation}

        # MAINLINE or SIDELINE -- a real, known continuation, even if not
        # the single most common one. Keep walking.

    if covered_plies == 0:
        return {
            "deviation": Deviation(
                status="book_unavailable",
                note="The Explorer has no data for this opening.",
            )
        }

    return {
        "deviation": Deviation(
            status="followed_theory",
            note="The game stayed within known theory for its full length.",
        )
    }


async def _extend_better_line(
    state: OpeningState,
    deviation: Deviation,
    deviation_service: OpeningDeviationService,
    max_extra_plies: int = MAX_BETTER_LINE_EXTRA_PLIES,
) -> Deviation:
    moves = state.get("moves", [])
    deviation_index = next(
        (i for i, move in enumerate(moves) if move["move_number"] == deviation.ply),
        None,
    )

    if deviation_index is None or deviation.better_move_san is None:
        return deviation

    board = chess.Board(moves[deviation_index]["fen_before"])
    move = chess.Move.from_uci(deviation.better_move_uci)

    if move not in board.legal_moves:
        return deviation

    line = [deviation.better_move_san]
    board.push(move)

    for _ in range(max_extra_plies):
        candidate = await deviation_service.best_candidate(board.fen())

        if candidate is None:
            break

        try:
            candidate_move = chess.Move.from_uci(candidate.uci)
        except ValueError:
            break

        if candidate_move not in board.legal_moves:
            break

        line.append(candidate.san or board.san(candidate_move))
        board.push(candidate_move)

    return deviation.model_copy(update={"better_line_san": line})


async def evaluate_mistakes(state: OpeningState, max_plies: int) -> dict:
    """Batch-evaluate the opening phase with Stockfish for objective blunders.

    Runs concurrently with `fetch_model_games`/`fetch_strategic_context` (see
    graph.py's parallel edges). Uses `aannotate_moves` so every position in
    the window is submitted to the process pool up front and awaited
    concurrently, instead of one Stockfish call at a time.
    """
    moves = state.get("moves", [])[:max_plies]

    if not moves:
        return {"branch_results": {"critical_mistakes": []}}

    analysis = await aannotate_moves(moves)
    mistakes: list[CriticalMistake] = []

    for move, annotated in zip(moves, analysis["moves"]):
        quality = annotated["quality"]

        if quality not in MISTAKE_SEVERITIES:
            continue

        mistakes.append(
            build_critical_mistake(
                move=move,
                quality=quality,
                cp_loss=annotated["cp_loss"] or 0,
                best_move_san=_uci_to_san(move["fen_before"], annotated.get("best_move_uci")),
            )
        )

    return {"branch_results": {"critical_mistakes": mistakes[:4]}}


def fetch_model_games(state: OpeningState) -> dict:
    eco = state.get("opening", OpeningIdentity()).eco
    return {"branch_results": {"model_games": get_model_games(eco)}}


def fetch_strategic_context(state: OpeningState) -> dict:
    eco = state.get("opening", OpeningIdentity()).eco
    themes, plans = get_strategic_context(eco)

    return {
        "branch_results": {
            "strategic_themes": themes,
            "middlegame_plans": plans,
        }
    }


def assemble_report(state: OpeningState) -> dict:
    return {"report": build_report(state)}


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
