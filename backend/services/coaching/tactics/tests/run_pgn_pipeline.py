from __future__ import annotations

import json
import sys
from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import Any

import chess
import chess.engine
import chess.pgn

from services.coaching.tactics.graph import build_tactics_graph
from services.coaching.tactics.schemas import AnnotatedMove
from services.coaching.tactics.strategic.models import (
    StrategicFact,
    fact_importance,
)


def score_to_white_cp(
    score: chess.engine.PovScore,
    mate_score: int = 100_000,
) -> int:
    """Converts engine score into centipawns from White's perspective."""
    return score.white().score(mate_score=mate_score)


def san_line_from_pv(
    board: chess.Board,
    pv: list[chess.Move],
) -> list[str]:
    """Converts a legal UCI/PV sequence to SAN from the root board."""
    working_board = board.copy(stack=False)
    san_moves: list[str] = []

    for move in pv:
        if move not in working_board.legal_moves:
            break

        san_moves.append(working_board.san(move))
        working_board.push(move)

    return san_moves


def classify_quality(cp_loss: int) -> str:
    if cp_loss >= 300:
        return "blunder"
    if cp_loss >= 100:
        return "mistake"
    if cp_loss >= 50:
        return "inaccuracy"
    return "good"


def strategic_fact_to_json(
    fact: StrategicFact,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "kind": fact.kind.value,
        "importance": fact_importance(fact),
    }

    for field in fields(fact):
        value = getattr(fact, field.name)

        if field.name == "moving_color":
            output[field.name] = (
                "white"
                if value == chess.WHITE
                else "black"
            )
            continue

        if field.name.endswith("_squares"):
            output[field.name] = [
                chess.square_name(square)
                for square in value
            ]
            continue

        if "_square" in field.name:
            output[field.name] = chess.square_name(value)
            continue

        if field.name == "piece_type" or field.name.endswith("_piece_type"):
            output[field.name] = chess.piece_name(value)
            continue

        if isinstance(value, Enum):
            output[field.name] = value.value
            continue

        output[field.name] = value

    return output


def analyse_game(
    pgn_path: Path,
    stockfish_path: str,
    depth: int = 16,
) -> list[AnnotatedMove]:
    with pgn_path.open(encoding="utf-8") as pgn_file:
        game = chess.pgn.read_game(pgn_file)

    if game is None:
        raise ValueError("No PGN game was found in the supplied file.")

    board = game.board()
    annotations: list[AnnotatedMove] = []

    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        for ply, played_move in enumerate(game.mainline_moves(), start=1):
            fen_before = board.fen()
            player_color = "white" if board.turn == chess.WHITE else "black"
            move_number = board.fullmove_number
            played_san = board.san(played_move)

            best_info = engine.analyse(
                board,
                chess.engine.Limit(depth=depth),
            )

            best_score_cp = score_to_white_cp(best_info["score"])
            best_pv: list[chess.Move] = best_info.get("pv", [])
            best_move = best_pv[0] if best_pv else None

            if played_move not in board.legal_moves:
                raise ValueError(
                    f"PGN contains illegal move at ply {ply}: "
                    f"{played_move.uci()}"
                )

            board_after_played = board.copy(stack=False)
            board_after_played.push(played_move)

            played_info = engine.analyse(
                board_after_played,
                chess.engine.Limit(depth=depth),
            )
            played_score_cp = score_to_white_cp(played_info["score"])

            if player_color == "white":
                cp_loss = max(0, best_score_cp - played_score_cp)
            else:
                cp_loss = max(0, played_score_cp - best_score_cp)

            mate_score = best_info["score"].relative.mate()
            mate_in_plies = (
                abs(mate_score)
                if mate_score is not None
                else None
            )

            annotations.append(
                AnnotatedMove(
                    ply=ply,
                    move_number=move_number,
                    color=player_color,
                    quality=classify_quality(cp_loss),
                    cp_loss=cp_loss,
                    fen_before=fen_before,
                    played_san=played_san,
                    played_uci=played_move.uci(),
                    best_move_san=(
                        board.san(best_move)
                        if best_move is not None
                        else None
                    ),
                    best_move_uci=(
                        best_move.uci()
                        if best_move is not None
                        else None
                    ),
                    principal_variation_uci=[
                        move.uci()
                        for move in best_pv
                    ],
                    principal_variation_san=san_line_from_pv(
                        board,
                        best_pv,
                    ),
                    mate_in_plies=mate_in_plies,
                    depth=depth,
                )
            )

            board.push(played_move)

    return annotations


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: uv run python -m "
            "services.coaching.tactics.run_pgn_pipeline "
            "<game.pgn> <stockfish-path>"
        )

    pgn_path = Path(sys.argv[1])
    stockfish_path = sys.argv[2]

    annotations = analyse_game(
        pgn_path=pgn_path,
        stockfish_path=stockfish_path,
        depth=16,
    )

    graph = build_tactics_graph()
    result = graph.invoke({"annotated_moves": annotations})

    report = result["report"]

    strategic_facts_by_ply = result.get(
        "strategic_facts_by_ply",
        {},
    )

    candidates_by_ply = {
        candidate.ply: candidate
        for candidate in result.get("candidates", [])
    }

    print("\n=== GAME METADATA ===")
    print(f"Annotated plies: {len(annotations)}")
    print(f"Valid moves: {len(result.get('valid_moves', []))}")
    print(f"Tactical candidates: {len(result.get('candidates', []))}")

    print("\n=== TACTICS REPORT ===")
    print(f"Headline: {report.headline}")
    print(f"Recurring pattern: {report.recurring_pattern}")

    for lesson in report.crucial_mistakes:
        print("\n--- Tactical Mistake ---")
        print(f"Move: {lesson.move_number} ({lesson.player_color})")
        print(f"Played: {lesson.played_move}")
        print(f"Better: {lesson.better_move}")
        print(f"Category: {lesson.category}")
        print(f"Motif: {lesson.motif}")
        print(f"Explanation: {lesson.explanation}")
        print(f"Calculation habit: {lesson.calculation_habit}")
        print(f"Confidence: {lesson.confidence}")

    print("\n=== STRATEGIC EXPLANATIONS ===")

    if not strategic_facts_by_ply:
        print("No strategic facts were returned by the graph.")

    for ply, facts in sorted(strategic_facts_by_ply.items()):
        if not facts:
            continue

        candidate = candidates_by_ply.get(ply)

        if candidate is not None:
            print(
                f"\n--- Ply {ply}: "
                f"{candidate.played_san} → {candidate.best_move_san} ---"
            )
        else:
            print(f"\n--- Ply {ply} ---")

        for fact in facts:
            print(
                json.dumps(
                    strategic_fact_to_json(fact),
                    indent=2,
                )
            )

    if report.input_issues:
        print("\n=== INPUT ISSUES ===")

        for issue in report.input_issues:
            print(
                f"[{issue.severity}] "
                f"ply={issue.ply}: "
                f"{issue.code} — {issue.message}"
            )

    Path("annotated_moves.json").write_text(
        json.dumps(
            [
                annotation.model_dump(mode="json")
                for annotation in annotations
            ],
            indent=2,
        )
    )

    Path("tactics_report.json").write_text(
        json.dumps(
            report.model_dump(mode="json"),
            indent=2,
        )
    )

    strategic_explanations_json = {
        str(ply): [
            strategic_fact_to_json(fact)
            for fact in facts
        ]
        for ply, facts in sorted(strategic_facts_by_ply.items())
        if facts
    }

    Path("strategic_explanations.json").write_text(
        json.dumps(
            strategic_explanations_json,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()