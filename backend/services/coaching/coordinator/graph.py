from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import node
from .state import CoordinatorState


def build_coordinator_graph():
    """Build the coordinator workflow.

    Purely sequential -- no parallel fan-out, no I/O, no Stockfish. Built
    as a LangGraph graph anyway so it can later be nested as a single node
    inside a top-level coaching graph that runs the opening/tactics agents
    as parallel subgraphs feeding into this one -- see the architecture
    plan's "Why LangGraph Here" section.
    """
    graph = StateGraph(CoordinatorState)

    graph.add_node("validate_inputs", node.validate_inputs)
    graph.add_node("normalize_and_merge", node.normalize_and_merge)
    graph.add_node("rank_lessons", node.rank_lessons)
    graph.add_node("aggregate_tactical_habits", node.aggregate_tactical_habits)
    graph.add_node("assemble_report", node.assemble_report_node)

    graph.add_edge(START, "validate_inputs")
    graph.add_edge("validate_inputs", "normalize_and_merge")
    graph.add_edge("normalize_and_merge", "rank_lessons")
    graph.add_edge("rank_lessons", "aggregate_tactical_habits")
    graph.add_edge("aggregate_tactical_habits", "assemble_report")
    graph.add_edge("assemble_report", END)

    return graph.compile()
