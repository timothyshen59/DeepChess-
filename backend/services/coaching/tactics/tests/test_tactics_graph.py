from __future__ import annotations

import unittest
import pprint

from services.coaching.tactics.graph import build_tactics_graph
from services.coaching.tactics.pipeline.candidate_selection import (
    MAX_DEEP_CANDIDATE_POOL,
    MAX_DEEP_CANDIDATES,
    SERIOUS_CP_LOSS,
    select_top_candidates,
)
from services.coaching.tactics.pipeline.deep_analysis import (
    run_deep_analysis,
    run_deep_analysis_with_backfill,
)
from services.coaching.tactics.schemas import AnnotatedMove, TacticalCandidate
from services.stockfish import MoveEvaluation


def _no_op_deep_analysis(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
    """Fake analyze_batch: deep analysis unavailable for every candidate --
    falls back to shallow-pass values, which is exactly what these
    existing tests already assert against. Keeps them Stockfish-free."""
    return [None] * len(requests)


def _make_candidate(ply: int, cp_loss: int, **overrides) -> TacticalCandidate:
    fields = {
        "ply": ply,
        "move_number": ply,
        "player_color": "white",
        "fen_before": "4k3/8/8/8/8/3q4/4Q3/4K3 w - - 0 1",
        "played_san": "Qe3",
        "played_uci": "e2e3",
        "best_move_san": "Qxd3",
        "best_move_uci": "e2d3",
        "principal_variation_uci": ["e2d3"],
        "cp_loss": cp_loss,
        "quality": "blunder",
    }
    fields.update(overrides)
    return TacticalCandidate(**fields)


class TacticsGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        # analyze_batch injected: these tests assert against shallow-pass
        # values (best_move_uci="Qxd3" etc., set directly on the
        # AnnotatedMove fixtures below), so the deep pass must be a no-op
        # here, not the real Stockfish-backed default.
        self.graph = build_tactics_graph(analyze_batch=_no_op_deep_analysis)

    def test_detects_defensive_hanging_queen(self) -> None:
        annotated_move = AnnotatedMove(
            ply=1,
            move_number=1,
            color="white",
            quality="blunder",
            cp_loss=900,
            fen_before="4k3/8/8/8/8/3q4/4Q3/4K3 w - - 0 1",
            played_san="Qe3",
            played_uci="e2e3",
            best_move_san="Qxd3",
            best_move_uci="e2d3",
            principal_variation_uci=["e2d3"],
            depth=18,
        )

        result = self.graph.invoke({"annotated_moves": [annotated_move]})

        print("\n\n========== GRAPH RESULT ==========")
        pprint.pprint(result)
        print("========== END GRAPH RESULT ==========\n")

        report = result["report"]

        self.assertEqual(len(report.input_issues), 0)
        self.assertEqual(len(report.crucial_mistakes), 1)

        lesson = report.crucial_mistakes[0]
        self.assertEqual(lesson.category, "defensive")
        self.assertEqual(lesson.motif, "hanging_piece")
        self.assertIn("immediate capture", lesson.explanation)

    def test_illegal_played_move_is_reported_without_crashing(self) -> None:
        annotated_move = AnnotatedMove(
            ply=1,
            move_number=1,
            color="white",
            quality="blunder",
            cp_loss=400,
            fen_before="4k3/8/8/8/8/8/3qQ3/4K3 w - - 0 1",
            played_san="Qh9",
            played_uci="e2h9",
            best_move_san="Qxd2",
            best_move_uci="e2d2",
        )

        result = self.graph.invoke({"annotated_moves": [annotated_move]})
        report = result["report"]

        self.assertEqual(len(report.crucial_mistakes), 0)
        self.assertEqual(len(report.input_issues), 1)
        self.assertEqual(report.input_issues[0].code, "illegal_played_move")


class SelectTopCandidatesTest(unittest.TestCase):
    """Pure/deterministic ranking+cap logic -- no Stockfish, no graph."""

    def test_caps_at_max_deep_candidates_ranked_by_cp_loss_desc(self) -> None:
        candidates = [_make_candidate(ply=i, cp_loss=i * 10) for i in range(1, 9)]

        top = select_top_candidates(candidates)

        self.assertEqual(len(top), MAX_DEEP_CANDIDATES)
        self.assertEqual([c.cp_loss for c in top], sorted((c.cp_loss for c in candidates), reverse=True)[:MAX_DEEP_CANDIDATES])

    def test_fewer_than_limit_returns_all_unchanged(self) -> None:
        candidates = [_make_candidate(ply=1, cp_loss=500), _make_candidate(ply=2, cp_loss=200)]

        top = select_top_candidates(candidates)

        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].cp_loss, 500)

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(select_top_candidates([]), [])


class RunDeepAnalysisTest(unittest.TestCase):
    """Verifies the architectural constraints your spec called out
    directly: exactly one batch call, real arguments passed through,
    per-candidate failure doesn't drop or crash the others, empty input
    never touches Stockfish at all."""

    def test_calls_analyze_batch_exactly_once_with_candidate_fen_and_move(self) -> None:
        candidates = [
            _make_candidate(ply=1, cp_loss=900, fen_before="fen-1", played_uci="e2e3"),
            _make_candidate(ply=2, cp_loss=300, fen_before="fen-2", played_uci="d7d5"),
        ]
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return [None] * len(requests)

        run_deep_analysis(candidates, analyze_batch=spy)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [("fen-1", "e2e3"), ("fen-2", "d7d5")])

    def test_merges_successful_deep_result_into_candidate(self) -> None:
        candidate = _make_candidate(
            ply=1, cp_loss=900, best_move_uci="e2d3", principal_variation_uci=["e2d3"]
        )
        deep_result = MoveEvaluation(
            best_move_uci="e2f3",
            best_move_san="Qf3",
            cp_loss=750,
            pv_uci=["e2f3", "e8d7"],
            pv_san=["Qf3", "Kd7"],
            depth=32,
        )

        merged = run_deep_analysis([candidate], analyze_batch=lambda requests: [deep_result])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].best_move_uci, "e2f3")
        self.assertEqual(merged[0].cp_loss, 750)
        self.assertEqual(merged[0].principal_variation_uci, ["e2f3", "e8d7"])
        self.assertEqual(merged[0].depth, 32)

    def test_per_candidate_failure_falls_back_to_shallow_values_without_dropping_it(self) -> None:
        ok_candidate = _make_candidate(ply=1, cp_loss=900, best_move_uci="e2d3")
        failed_candidate = _make_candidate(ply=2, cp_loss=300, best_move_uci="d7d5")
        deep_result = MoveEvaluation(
            best_move_uci="e2f3",
            best_move_san="Qf3",
            cp_loss=750,
            pv_uci=["e2f3"],
            pv_san=["Qf3"],
            depth=32,
        )

        merged = run_deep_analysis(
            [ok_candidate, failed_candidate],
            analyze_batch=lambda requests: [deep_result, None],
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].best_move_uci, "e2f3")
        # Deep analysis failed for the second candidate -- its shallow-pass
        # value is preserved, it isn't dropped from the result.
        self.assertEqual(merged[1].best_move_uci, "d7d5")
        self.assertEqual(merged[1].cp_loss, 300)

    def test_empty_candidates_never_calls_analyze_batch(self) -> None:
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return []

        result = run_deep_analysis([], analyze_batch=spy)

        self.assertEqual(result, [])
        self.assertEqual(len(calls), 0)


def _deep_result(cp_loss: int) -> MoveEvaluation:
    return MoveEvaluation(
        best_move_uci="e2f3",
        best_move_san="Qf3",
        cp_loss=cp_loss,
        pv_uci=["e2f3"],
        pv_san=["Qf3"],
        depth=32,
    )


class RunDeepAnalysisWithBackfillTest(unittest.TestCase):
    """Covers exactly the scenario from the conversation: the deep pass can
    disprove a shallow-flagged candidate (corrected cp_loss below
    SERIOUS_CP_LOSS), and backfill must draw from the next-ranked
    candidates -- but never look past MAX_DEEP_CANDIDATE_POOL, and accept
    fewer than MAX_DEEP_CANDIDATES validated mistakes if the pool runs out.
    """

    def test_no_backfill_needed_when_first_batch_all_validate(self) -> None:
        candidates = [_make_candidate(ply=i, cp_loss=500) for i in range(1, 5)]
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return [_deep_result(500) for _ in requests]

        validated = run_deep_analysis_with_backfill(candidates, analyze_batch=spy)

        self.assertEqual(len(validated), MAX_DEEP_CANDIDATES)
        self.assertEqual(len(calls), 1, "one round, no backfill, when nothing needs it")
        self.assertEqual(sum(len(c) for c in calls), 4)

    def test_backfills_from_next_ranked_candidates_when_some_fail_validation(self) -> None:
        # 6 high-recall candidates, ranked 1..6 by shallow cp_loss. The
        # first 4 (the initial attempt) include two false positives the
        # deep pass will disprove (cp_loss corrected below the mistake
        # bar) -- backfill must pull candidates 5 and 6 to try to replace
        # them, not just accept a shrunken report.
        candidates = [_make_candidate(ply=i, cp_loss=1000 - i, fen_before=f"fen-{i}") for i in range(1, 7)]
        deep_cp_loss_by_fen = {
            "fen-1": 900,  # real mistake, survives
            "fen-2": 5,  # false positive, disproven
            "fen-3": 800,  # real mistake, survives
            "fen-4": 3,  # false positive, disproven
            "fen-5": 700,  # backfill candidate, real mistake
            "fen-6": 600,  # backfill candidate, real mistake (not needed if fen-5 alone covers the shortfall)
        }
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return [_deep_result(deep_cp_loss_by_fen[fen]) for fen, _ in requests]

        validated = run_deep_analysis_with_backfill(candidates, analyze_batch=spy)

        self.assertEqual(len(validated), MAX_DEEP_CANDIDATES)
        self.assertEqual(len(calls), 2, "exactly one backfill round")
        total_attempted = sum(len(c) for c in calls)
        self.assertLessEqual(total_attempted, MAX_DEEP_CANDIDATE_POOL)
        # The two disproven candidates must not appear in the final result.
        self.assertTrue(all(c.cp_loss >= SERIOUS_CP_LOSS for c in validated))

    def test_never_exceeds_the_pool_ceiling_even_if_everything_keeps_failing(self) -> None:
        # Far more high-recall candidates than the pool ceiling -- every
        # single one turns out to be a false positive once deep-analyzed.
        candidates = [_make_candidate(ply=i, cp_loss=1000 - i, fen_before=f"fen-{i}") for i in range(1, 21)]
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return [_deep_result(0) for _ in requests]  # every candidate disproven

        validated = run_deep_analysis_with_backfill(candidates, analyze_batch=spy)

        self.assertEqual(validated, [], "fewer than MAX_DEEP_CANDIDATES survives -- that's accepted, not an error")
        total_attempted = sum(len(c) for c in calls)
        self.assertEqual(
            total_attempted,
            MAX_DEEP_CANDIDATE_POOL,
            "must stop exactly at the pool ceiling, never search the other 10 candidates",
        )

    def test_empty_input_never_calls_analyze_batch(self) -> None:
        calls: list[list[tuple[str, str]]] = []

        def spy(requests: list[tuple[str, str]]) -> list[MoveEvaluation | None]:
            calls.append(requests)
            return []

        validated = run_deep_analysis_with_backfill([], analyze_batch=spy)

        self.assertEqual(validated, [])
        self.assertEqual(len(calls), 0)


if __name__ == "__main__":
    unittest.main()
