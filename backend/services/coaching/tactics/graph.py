from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from services.stockfish import analyze_tactical_candidates_batch

from .node import (
    assemble_tactics_report,
    compute_best_move_features,
    compute_played_move_features,
    compute_pv_features,
    rank_and_select_candidates,
    run_deep_analysis_node,
    select_tactical_candidates,
    validate_annotated_moves,
    strategic_explanations,
)
from .pipeline.deep_analysis import AnalyzeBatch
from .state import TacticsState


def build_tactics_graph(analyze_batch: AnalyzeBatch = analyze_tactical_candidates_batch):
    """Build a parallel deterministic tactical-coaching workflow.

    `analyze_batch` defaults to the real Stockfish-backed deep-analysis
    call -- production callers (pipeline.py::run_tactics) never need to
    pass it. Tests inject a fake so the whole graph stays hermetic and
    directly call-counted/argument-asserted, with no real Stockfish binary
    needed (see tactics/tests/test.py).
    """
    graph = StateGraph(TacticsState)

    def _deep_analysis(state: TacticsState) -> dict:
        return run_deep_analysis_node(state, analyze_batch=analyze_batch)

    graph.add_node("validate_moves", validate_annotated_moves)
    graph.add_node("select_candidates", select_tactical_candidates)
    graph.add_node("rank_candidates", rank_and_select_candidates)
    graph.add_node("deep_analysis", _deep_analysis)
    graph.add_node("best_move_features", compute_best_move_features)
    graph.add_node("played_move_features", compute_played_move_features)
    graph.add_node("pv_features", compute_pv_features)
    graph.add_node("assemble_report", assemble_tactics_report)
    graph.add_node("strategic_explanations", strategic_explanations)

    graph.add_edge(START, "validate_moves")
    graph.add_edge("validate_moves", "select_candidates")
    graph.add_edge("select_candidates", "rank_candidates")
    graph.add_edge("rank_candidates", "deep_analysis")

    graph.add_edge("deep_analysis", "best_move_features")
    graph.add_edge("deep_analysis", "played_move_features")
    graph.add_edge("deep_analysis", "pv_features")

    graph.add_edge("best_move_features", "assemble_report")
    graph.add_edge("played_move_features", "assemble_report")
    graph.add_edge("pv_features", "assemble_report")

    graph.add_edge("assemble_report", "strategic_explanations")
    graph.add_edge("strategic_explanations", END)

    return graph.compile()
