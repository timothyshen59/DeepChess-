from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .node import (
    assemble_tactics_report,
    compute_best_move_features,
    compute_played_move_features,
    compute_pv_features,
    select_tactical_candidates,
    validate_annotated_moves,
    strategic_explanations

)
from .state import TacticsState


def build_tactics_graph():
    """Build a parallel deterministic tactical-coaching workflow."""
    graph = StateGraph(TacticsState)

    graph.add_node("validate_moves", validate_annotated_moves)
    graph.add_node("select_candidates", select_tactical_candidates)
    graph.add_node("best_move_features", compute_best_move_features)
    graph.add_node("played_move_features", compute_played_move_features)
    graph.add_node("pv_features", compute_pv_features)
    graph.add_node("assemble_report", assemble_tactics_report)
    graph.add_node("strategic_explanations", strategic_explanations)

    graph.add_edge(START, "validate_moves")
    graph.add_edge("validate_moves", "select_candidates")

    graph.add_edge("select_candidates", "best_move_features")
    graph.add_edge("select_candidates", "played_move_features")
    graph.add_edge("select_candidates", "pv_features")

    graph.add_edge("best_move_features", "assemble_report")
    graph.add_edge("played_move_features", "assemble_report")
    graph.add_edge("pv_features", "assemble_report")

    graph.add_edge("assemble_report", "strategic_explanations")
    graph.add_edge("strategic_explanations", END)

    return graph.compile()