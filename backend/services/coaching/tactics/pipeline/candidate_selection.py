from __future__ import annotations

import os

from ..schemas import AnnotatedMove, TacticalCandidate


SERIOUS_CP_LOSS = 100
TACTICAL_QUALITIES = frozenset({"mistake", "blunder"})

# How many validated tactical mistakes the deep pass tries to surface.
# Matches TacticsReport.crucial_mistakes's existing max_length=4 -- not a
# new number, just enforced earlier now (before the deep pass runs, not
# after, at report-assembly time).
MAX_DEEP_CANDIDATES = int(os.getenv("MAX_DEEP_CANDIDATES", "4"))

# Hard ceiling on how many high-recall candidates are even eligible for
# the deep pass -- the initial attempt plus every backfill round combined.
# Bounds worst-case Stockfish cost to this many deep searches, no matter
# how many moves the shallow pass flagged in a genuinely bad game. Backfill
# only ever draws from this top-10-by-shallow-cp_loss pool, never beyond
# it -- fewer than MAX_DEEP_CANDIDATES validated mistakes surviving after
# exhausting the pool is an accepted outcome, not an error.
MAX_DEEP_CANDIDATE_POOL = int(os.getenv("MAX_DEEP_CANDIDATE_POOL", "10"))


def select_candidates(valid_moves: list[AnnotatedMove]) -> list[TacticalCandidate]:
    """Select moves that warrant tactical feature extraction."""
    candidates: list[TacticalCandidate] = []

    for move in valid_moves:
        has_large_loss = move.cp_loss >= SERIOUS_CP_LOSS
        has_tactical_label = move.quality in TACTICAL_QUALITIES

        if not has_large_loss and not has_tactical_label:
            continue

        candidates.append(
            TacticalCandidate(
                ply=move.ply,
                move_number=move.move_number,
                player_color=move.color,
                fen_before=move.fen_before,
                played_san=move.played_san,
                played_uci=move.played_uci,
                best_move_san=move.best_move_san,
                best_move_uci=move.best_move_uci,
                principal_variation_uci=move.principal_variation_uci,
                cp_loss=move.cp_loss,
                quality=move.quality,
                mate_in_plies=move.mate_in_plies,
                depth=move.depth,
            )
        )

    return candidates


def rank_candidates(candidates: list[TacticalCandidate]) -> list[TacticalCandidate]:
    """Rank select_candidates()'s high-recall output by shallow-pass
    cp_loss, most severe first. Pure/deterministic, no Stockfish involved,
    same as select_candidates() itself. Does not cut anything -- callers
    that need a hard cap (deep_analysis's backfill pool) slice this
    themselves against MAX_DEEP_CANDIDATE_POOL."""
    return sorted(candidates, key=lambda candidate: candidate.cp_loss, reverse=True)


def select_top_candidates(
    candidates: list[TacticalCandidate],
    limit: int = MAX_DEEP_CANDIDATES,
) -> list[TacticalCandidate]:
    """Convenience: rank_candidates() + cut to `limit`."""
    return rank_candidates(candidates)[:limit]


def is_validated_mistake(candidate: TacticalCandidate) -> bool:
    """Whether a candidate's cp_loss -- after whichever analysis pass most
    recently updated it -- still clears the bar to count as a real
    tactical mistake, not a shallow-pass false positive the deep pass
    disproved."""
    return candidate.cp_loss >= SERIOUS_CP_LOSS
