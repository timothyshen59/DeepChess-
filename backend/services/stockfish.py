import asyncio
import atexit
import multiprocessing.util
import os
import logging


import chess
import chess.engine

from concurrent.futures import ProcessPoolExecutor

from pydantic import BaseModel

logger = logging.getLogger(__name__)

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
STOCKFISH_NODES = int(os.getenv("STOCKFISH_NODES", "100_000"))
STOCKFISH_THREADS = int(os.getenv("STOCKFISH_THREADS", "1"))
STOCKFISH_HASH_MB = int(os.getenv("STOCKFISH_HASH_MB", "64"))
MAX_FAILURE_RATE = float(os.getenv("MAX_FAILURE_RATE", "0.10"))
MATE_SCORE = 10_000

PV_LENGTH = 5

TACTICAL_ANALYSIS_DEPTH = 25
TACTICAL_PV_LIMIT = 8

QUALITY_THRESHOLDS = [
    ("brilliant", float("-inf"), 0),
    ("good", 0, 10),
    ("inaccuracy", 10, 25),
    ("mistake", 25, 100),
    ("blunder", 100, float("inf")),
]

QUALITY_COLORS = {
    "brilliant": "#1baca6",
    "good": "#6faf72",
    "inaccuracy": "#f0c15f",
    "mistake": "#e07b35",
    "blunder": "#c93b3b",
    "unknown": "#888888",
}


class MoveEvaluation(BaseModel):
    """Neutral engine-evaluation result, owned by this infra module.

    Feature modules (tactics, opening, ...) should import this type *from*
    stockfish.py rather than stockfish.py importing a feature-specific type —
    keeps the dependency direction pointing from features to infra, not back.
    """

    best_move_uci: str
    best_move_san: str
    cp_loss: int
    pv_uci: list[str]
    pv_san: list[str]
    depth: int
    mate_in_plies: int | None = None


class StockfishUnavailableError(RuntimeError):
    """Stockfish or the analysis worker pool cannot be used."""


class StockfishAnalysisError(RuntimeError):
    """A game analysis cannot produce a reliable result."""


_ENGINE: chess.engine.SimpleEngine | None = None
_EXECUTOR: ProcessPoolExecutor | None = None


def _start_stockfish_worker(stockfish_path: str, threads: int, hash_mb: int) -> None:
    global _ENGINE

    try:
        _ENGINE = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        _ENGINE.configure(
            {
                "Threads": threads,
                "Hash": hash_mb,
            }
        )

        # SimpleEngine runs UCI communication on a non-daemon background
        # thread. Without closing it, a worker that has evaluated at least
        # one position never fully exits, and stop_stockfish_pool()'s
        # executor.shutdown(wait=True) hangs forever waiting to join it.
        #
        # A plain atexit.register() here does NOT work: multiprocessing's
        # own worker bootstrap (multiprocessing/process.py::BaseProcess.
        # _bootstrap) calls threading._shutdown() -- which blocks joining
        # this exact background thread -- directly, before the interpreter
        # ever reaches its normal atexit sweep. multiprocessing.util.Finalize
        # registers with multiprocessing's *own* exit-finalizer list, which
        # util._exit_function() runs earlier, before that thread-join.
        multiprocessing.util.Finalize(None, _ENGINE.close, exitpriority=0)

    except Exception as error:
        logger.exception(
            "Stockfish worker failed to start. path=%s threads=%s hash_mb=%s",
            stockfish_path,
            threads,
            hash_mb,
        )
        raise StockfishUnavailableError("Stockfish worker could not start.") from error


def start_stockfish_pool() -> None:
    """Call once during FastAPI lifespan startup"""
    global _EXECUTOR

    if _EXECUTOR is not None:
        return

    try:
        _EXECUTOR = ProcessPoolExecutor(
            max_workers=MAX_WORKERS,
            initializer=_start_stockfish_worker,
            initargs=(
                STOCKFISH_PATH,
                STOCKFISH_THREADS,
                STOCKFISH_HASH_MB,
            ),
        )

        logger.info(
            "Created Stockfish process pool. workers=%s nodes=%s",
            MAX_WORKERS,
            STOCKFISH_NODES,
        )

    except Exception as error:
        logger.exception("Could not create Stockfish process pool.")
        raise StockfishUnavailableError("Stockfish analysis service is unavailable.") from error


def stop_stockfish_pool() -> None:
    """Call once during FastAPI shutdown"""
    global _EXECUTOR

    if _EXECUTOR is None:
        return

    logger.info("Stopping Stockfish process pool.")

    _EXECUTOR.shutdown(wait=True, cancel_futures=True)
    _EXECUTOR = None


def _get_executor() -> ProcessPoolExecutor:
    if _EXECUTOR is None:
        raise StockfishUnavailableError("Stockfish pool has not started.")

    return _EXECUTOR


def cp_loss_to_quality(cp_loss: float | None) -> str:
    if cp_loss is None:
        return "unknown"

    for quality, lower, upper in QUALITY_THRESHOLDS:
        if lower <= cp_loss < upper:
            return quality

    return "unknown"


def _calculate_cp_loss(
    best_eval_cp: int | None, played_eval_cp: int | None, color: str
) -> int | None:
    if best_eval_cp is None or played_eval_cp is None:
        return None

    if color == "white":
        return max(0, best_eval_cp - played_eval_cp)

    return max(0, played_eval_cp - best_eval_cp)


# TODO: Rewrite with more better varialbe names
def _evaluate_move(fen_before: str, move_uci: str) -> dict:
    try:
        if _ENGINE is None:
            raise RuntimeError("Stockfish worker has not started.")

        board = chess.Board(fen_before)
        played_move = chess.Move.from_uci(move_uci)

        if played_move not in board.legal_moves:
            raise ValueError(f"Illegal move: {move_uci}")

        # _ENGINE is one persistent Stockfish process reused for every
        # position this worker ever evaluates (its whole process lifetime,
        # across every test case in a session) -- and python-chess only
        # sends "ucinewgame" (which clears the hash table) once, the very
        # first time analyse() is ever called on it, since we never pass a
        # `game=` token (chess/engine.py's UciProtocol.analysis: it fires
        # ucinewgame only when self.engine.game != game, and game defaults
        # to None on both sides forever). Without this, the hash table
        # accumulates entries from every unrelated prior position, and
        # since ProcessPoolExecutor hands positions to whichever of
        # MAX_WORKERS happens to be free, which worker (with which prior
        # history) evaluates a given position is not reproducible run to
        # run -- so the same STOCKFISH_NODES budget can still explore a
        # different line. Clearing once per position (not before the
        # second analyse() call below -- that one's the same position, so
        # reusing what the first call just populated is correct) makes
        # every evaluation start from identical, position-independent
        # state.
        _ENGINE.configure({"Clear Hash": None})

        best_info = _ENGINE.analyse(board, chess.engine.Limit(nodes=STOCKFISH_NODES))

        best_eval_cp = best_info["score"].white().score(mate_score=MATE_SCORE)
        best_move_uci = best_info["pv"][0].uci()
        principal_variation = [pv_move.uci() for pv_move in best_info.get("pv", [])[:PV_LENGTH]]

        if move_uci == best_move_uci:
            played_eval_cp = best_eval_cp

        else:
            played_info = _ENGINE.analyse(
                board, chess.engine.Limit(nodes=STOCKFISH_NODES), root_moves=[played_move]
            )
            played_eval_cp = played_info["score"].white().score(mate_score=MATE_SCORE)

        return {
            "ok": True,
            "best_eval_cp": best_eval_cp,
            "played_eval_cp": played_eval_cp,
            "principal_variation": principal_variation,
            "best_move_uci": best_move_uci,
            "error": None,
        }
    except Exception as exc:
        import traceback

        print(f"STOCKFISH WORKER ERROR for {move_uci}:\n{traceback.format_exc()}")

        return {
            "ok": False,
            "best_eval_cp": None,
            "played_eval_cp": None,
            "principal_variation": None,
            "best_move_uci": None,
            "error": str(exc),
        }


def _submit_evaluations(executor: ProcessPoolExecutor, moves: list[dict]) -> list:
    return [
        executor.submit(
            _evaluate_move,
            move["fen_before"],
            move["move_uci"],
        )
        for move in moves
    ]


def _finalize_annotations(moves: list[dict], results: list[dict]) -> dict:
    failed_positions = sum(not result["ok"] for result in results)
    total_positions = len(results)

    if failed_positions / total_positions > MAX_FAILURE_RATE:
        raise StockfishAnalysisError("Too many positions failed to evaluate.")

    annotated = []

    for move, result in zip(moves, results):
        cp_loss = _calculate_cp_loss(
            best_eval_cp=result["best_eval_cp"],
            played_eval_cp=result["played_eval_cp"],
            color=move["color"],
        )

        quality = cp_loss_to_quality(cp_loss)

        annotated.append(
            {
                **move,
                "cp_loss": cp_loss,
                "best_move_uci": result["best_move_uci"],
                "principal_variation": result["principal_variation"],
                "quality": quality,
                "color_hex": QUALITY_COLORS[quality],
            }
        )

    return {
        "moves": annotated,
        "failed_positions": failed_positions,
        "total_positions": total_positions,
        "is_partial": failed_positions > 0,
    }


def annotate_moves(moves: list[dict]) -> dict:
    if not moves:
        return {
            "moves": [],
            "failed_positions": 0,
            "total_positions": 0,
            "is_partial": False,
        }

    executor = _get_executor()
    futures = _submit_evaluations(executor, moves)
    results = [future.result() for future in futures]

    return _finalize_annotations(moves, results)


async def aannotate_moves(moves: list[dict]) -> dict:
    """Async-friendly sibling of `annotate_moves`.

    Submits the same per-position work to the existing ProcessPoolExecutor,
    then awaits every future concurrently via `asyncio.wrap_future` instead
    of blocking the calling thread with `future.result()`. This lets an
    async caller (e.g. the opening agent's graph) overlap a whole batch of
    positions with other async work rather than stalling the event loop on
    it, and evaluates every position in the batch concurrently rather than
    one at a time.
    """
    if not moves:
        return {
            "moves": [],
            "failed_positions": 0,
            "total_positions": 0,
            "is_partial": False,
        }

    executor = _get_executor()
    futures = _submit_evaluations(executor, moves)
    results = await asyncio.gather(*(asyncio.wrap_future(future) for future in futures))

    return _finalize_annotations(moves, results)


def analyze_tactical_candidate(fen_before: str, played_move_uci: str) -> MoveEvaluation:
    if _ENGINE is None:
        raise RuntimeError("Stockfish worker has not started")

    board = chess.Board(fen_before)
    played_move = chess.Move.from_uci(played_move_uci)

    if played_move not in board.legal_moves:
        raise ValueError(f"Illegal move: {played_move_uci}")

    limit = chess.engine.Limit(depth=TACTICAL_ANALYSIS_DEPTH)
    analysis = _ENGINE.analyse(board, limit)

    pv = analysis["pv"][:TACTICAL_PV_LIMIT]

    if not pv:
        raise RuntimeError("Stockfish returned no principal variation.")

    evaluation = analysis["score"].pov(board.turn)
    evaluation_cp = evaluation.score(mate_score=MATE_SCORE)
    mate_in_plies = evaluation.mate()

    if pv[0] == played_move:
        move_cp = evaluation_cp
    else:
        player_analysis = _ENGINE.analyse(board, limit, root_moves=[played_move])
        move_cp = player_analysis["score"].pov(board.turn).score(mate_score=MATE_SCORE)

    position = board.copy()
    pv_san = []

    for move in pv:
        pv_san.append(position.san(move))
        position.push(move)

    return MoveEvaluation(
        best_move_uci=pv[0].uci(),
        best_move_san=board.san(pv[0]),
        cp_loss=max(0, evaluation_cp - move_cp),
        pv_uci=[move.uci() for move in pv],
        pv_san=pv_san,
        depth=TACTICAL_ANALYSIS_DEPTH,
        mate_in_plies=mate_in_plies,
    )


atexit.register(stop_stockfish_pool)
