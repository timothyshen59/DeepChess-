from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from langgraph.graph import END, START, StateGraph

from services.opening_deviation.deviation.service import OpeningDeviationService

from . import node
from .eco.eco_index import EcoIndex
from .state import OpeningState


@dataclass(frozen=True, slots=True)
class OpeningDeps:
    """Dependencies injected into the graph's nodes.

    Passed in at graph-build time (not read from module-level globals), so
    tests can substitute fakes for the ECO index / deviation engine without
    touching real dataset files, a live Explorer API, or Stockfish.
    """

    eco_index: EcoIndex
    deviation_service: OpeningDeviationService
    theory_max_plies: int = 30


def build_opening_graph(deps: OpeningDeps):
    """Build the opening-coaching workflow.

    Only `evaluate_mistakes` is `async def` (the only node doing real, slow
    work). Plain sync nodes are auto-offloaded to a thread by LangGraph's
    `coerce_to_runnable` under `.ainvoke()`, so they don't need to be async
    themselves -- see the architecture plan's "sync vs. async nodes"
    decision.
    """
    graph = StateGraph(OpeningState)

    graph.add_node("parse_input", node.parse_input)
    graph.add_node(
        "identify_opening",
        partial(node.identify_opening, eco_index=deps.eco_index),
    )
    graph.add_node(
        "compute_deviation",
        partial(
            node.compute_deviation,
            deviation_service=deps.deviation_service,
            max_plies=deps.theory_max_plies,
        ),
    )
    graph.add_node(
        "evaluate_mistakes",
        partial(node.evaluate_mistakes, max_plies=deps.theory_max_plies),
    )
    graph.add_node("fetch_model_games", node.fetch_model_games)
    graph.add_node("fetch_strategic_context", node.fetch_strategic_context)
    graph.add_node("assemble_report", node.assemble_report)

    graph.add_edge(START, "parse_input")
    graph.add_edge("parse_input", "identify_opening")
    graph.add_edge("identify_opening", "compute_deviation")

    # Parallel fan-out: these three branches are independent of one another,
    # mirroring tactics/graph.py's three-branch pattern. LangGraph's pregel
    # runtime schedules ready async/sync nodes concurrently under
    # `.ainvoke()`, so the (slow) Stockfish batch in `evaluate_mistakes`
    # overlaps with the two static-lookup branches instead of queueing
    # behind them.
    graph.add_edge("compute_deviation", "evaluate_mistakes")
    graph.add_edge("compute_deviation", "fetch_model_games")
    graph.add_edge("compute_deviation", "fetch_strategic_context")

    graph.add_edge("evaluate_mistakes", "assemble_report")
    graph.add_edge("fetch_model_games", "assemble_report")
    graph.add_edge("fetch_strategic_context", "assemble_report")

    graph.add_edge("assemble_report", END)

    return graph.compile()
