"""
Infra adapter bridging the tactics domain (TacticalCandidate) and
services.stockfish's deep-analysis infra call. This is the one place in
the tactics agent that talks to Stockfish for the deep pass -- everything
downstream (best_move_features, played_move_features, pv_features)
consumes whatever this produces and never calls Stockfish itself.
"""

from __future__ import annotations

from typing import Callable

from services.stockfish import MoveEvaluation, analyze_tactical_candidates_batch

from ..schemas import TacticalCandidate
from .candidate_selection import (
    MAX_DEEP_CANDIDATE_POOL,
    MAX_DEEP_CANDIDATES,
    is_validated_mistake,
)

AnalyzeBatch = Callable[[list[tuple[str, str]]], list[MoveEvaluation | None]]


def run_deep_analysis(
    candidates: list[TacticalCandidate],
    analyze_batch: AnalyzeBatch = analyze_tactical_candidates_batch,
) -> list[TacticalCandidate]:
    """Deep-analyze each candidate and merge the result back in.

    `analyze_batch` defaults to the real Stockfish-backed infra call but is
    an explicit parameter -- production wiring never needs to pass it, unit
    tests inject a fake and get a hermetic, Stockfish-free, directly
    call-counted/argument-asserted test (see tactics/tests/test.py).

    A candidate whose deep analysis fails (the batch call returns `None`
    for it -- Stockfish timeout, error, or no PV, see
    analyze_tactical_candidates_batch's own per-request handling) keeps its
    original shallow-pass values rather than being dropped: one bad
    candidate shouldn't shrink the final report.
    """
    if not candidates:
        return []

    requests = [(candidate.fen_before, candidate.played_uci) for candidate in candidates]
    results = analyze_batch(requests)

    merged: list[TacticalCandidate] = []

    for candidate, result in zip(candidates, results):
        if result is None:
            merged.append(candidate)
            continue

        merged.append(
            candidate.model_copy(
                update={
                    "best_move_uci": result.best_move_uci,
                    "best_move_san": result.best_move_san,
                    "cp_loss": result.cp_loss,
                    "principal_variation_uci": result.pv_uci,
                    "mate_in_plies": result.mate_in_plies,
                    "depth": result.depth,
                }
            )
        )

    return merged


def run_deep_analysis_with_backfill(
    ranked_candidates: list[TacticalCandidate],
    target: int = MAX_DEEP_CANDIDATES,
    pool_limit: int = MAX_DEEP_CANDIDATE_POOL,
    analyze_batch: AnalyzeBatch = analyze_tactical_candidates_batch,
) -> list[TacticalCandidate]:
    """Deep-analyze `ranked_candidates` (already sorted by shallow cp_loss,
    most severe first) until `target` validated mistakes are found or the
    top-`pool_limit` pool is exhausted -- whichever comes first.

    The deep pass can reveal a shallow-flagged candidate isn't a real
    mistake after all (see is_validated_mistake -- its corrected cp_loss no
    longer clears the bar). When that shrinks the validated set below
    `target`, this backfills from the next-ranked candidates that weren't
    in the first attempt, but never looks past `pool_limit` candidates
    total, no matter how many the shallow pass flagged. Fewer than `target`
    validated mistakes surviving after the pool is exhausted is an accepted
    outcome, not an error -- the caller gets a shorter list, not a retry.

    Runs in rounds sized to the current shortfall (round 1: up to `target`
    candidates; each backfill round: up to however many are still needed),
    so a game where nothing needs backfilling costs exactly one round of
    `target` deep searches, not the full pool every time.
    """
    pool = ranked_candidates[:pool_limit]
    validated: list[TacticalCandidate] = []
    already_attempted = 0

    while len(validated) < target and already_attempted < len(pool):
        shortfall = target - len(validated)
        batch = pool[already_attempted : already_attempted + shortfall]
        already_attempted += len(batch)

        analyzed = run_deep_analysis(batch, analyze_batch=analyze_batch)
        validated.extend(candidate for candidate in analyzed if is_validated_mistake(candidate))

    return validated[:target]
