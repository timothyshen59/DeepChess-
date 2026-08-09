"""
E2E regression suite: runs the real public coaching pipeline
(services.coaching.pipeline.run_coaching_pipeline) against a real PGN and
checks the result against a hand-written, manually-reviewed expected.json --
never a full-report snapshot, never exact explanation-text comparison.

Discovers tests/e2e/cases/*/ containing both game.pgn and expected.json.
Marked @pytest.mark.e2e; skips with a clear message if no usable Stockfish
binary is found via STOCKFISH_PATH (or services/stockfish.py's own default).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from services.coaching.coordinator.schemas import CoordinatedReport
from services.coaching.opening.eco.eco_index import EcoIndex
from services.coaching.opening.graph import OpeningDeps
from services.coaching.opening.schemas import OpeningReport
from services.coaching.opening.tests.fixtures.najdorf_fake_service import build_najdorf_fake_service
from services.coaching.pipeline import run_coaching_pipeline
from services.coaching.tactics.schemas import TacticsReport
from services.opening_deviation import deps as opening_deviation_deps
from services.stockfish import start_stockfish_pool, stop_stockfish_pool

CASES_DIR = Path(__file__).parent / "cases"


def discover_cases() -> list[Path]:
    """cases/*/ containing BOTH game.pgn and expected.json."""
    if not CASES_DIR.exists():
        return []

    return sorted(
        case_dir
        for case_dir in CASES_DIR.iterdir()
        if case_dir.is_dir()
        and (case_dir / "game.pgn").exists()
        and (case_dir / "expected.json").exists()
    )


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def stockfish_path() -> str:
    """Resolve the same way services/stockfish.py does -- STOCKFISH_PATH env
    var, falling back to its hardcoded default -- and skip with a clear
    message if nothing usable is found there."""
    path = os.getenv("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")

    if not (Path(path).is_file() and os.access(path, os.X_OK)):
        pytest.skip(
            f"No usable Stockfish binary at '{path}'. Set the STOCKFISH_PATH "
            "environment variable to run the E2E suite."
        )

    return path


@pytest.fixture(scope="session")
def stockfish_pool(stockfish_path):
    start_stockfish_pool()
    yield
    stop_stockfish_pool()


@pytest.fixture(scope="session")
def opening_deps(stockfish_pool) -> OpeningDeps:
    """Real EcoIndex (bundled dataset) + a deviation engine.

    Defaults to a fake `OpeningDeviationService` covering exactly the
    Najdorf line the deviation-related cases exercise (deterministic, safe
    for CI, no live network needed) -- set `OPENING_DEVIATION_E2E_LIVE=1`
    to use the real engine (services/opening_deviation, real cache + live
    Lichess Explorer) for a more meaningful local run against arbitrary
    games. Never assumed to be set: CI has no network access to Lichess,
    so the default must keep working with it unset.
    """
    eco_index = EcoIndex.load()

    if os.getenv("OPENING_DEVIATION_E2E_LIVE"):
        opening_deviation_deps.load_deps()
        deviation_service = opening_deviation_deps.get_service()
    else:
        deviation_service = build_najdorf_fake_service()

    yield OpeningDeps(eco_index=eco_index, deviation_service=deviation_service, theory_max_plies=30)


# --------------------------------------------------------------------------
# Assertion helpers
# --------------------------------------------------------------------------


def assert_opening_agent_expectations(expected: dict, report: OpeningReport) -> None:
    if "eco" in expected:
        assert report.opening.eco == expected["eco"], (
            f"opening.eco: expected {expected['eco']!r}, got {report.opening.eco!r}"
        )

    if "name_contains" in expected:
        name = report.opening.name or ""
        assert expected["name_contains"] in name, (
            f"opening.name: expected to contain {expected['name_contains']!r}, got {name!r}"
        )

    if "variation_contains" in expected:
        variation = report.opening.variation or ""
        assert expected["variation_contains"] in variation, (
            f"opening.variation: expected to contain "
            f"{expected['variation_contains']!r}, got {variation!r}"
        )

    if "minimum_matched_plies" in expected:
        assert report.opening.matched_plies >= expected["minimum_matched_plies"], (
            f"opening.matched_plies: expected >= {expected['minimum_matched_plies']}, "
            f"got {report.opening.matched_plies}"
        )

    if "deviation" in expected:
        _assert_deviation(expected["deviation"], report.deviation)

    if "minimum_critical_mistakes" in expected:
        assert len(report.critical_mistakes) >= expected["minimum_critical_mistakes"], (
            f"critical_mistakes: expected >= {expected['minimum_critical_mistakes']}, "
            f"got {len(report.critical_mistakes)}"
        )

    if "required_strategic_theme_titles" in expected:
        actual_titles = {theme.title for theme in report.strategic_themes}
        for required_title in expected["required_strategic_theme_titles"]:
            assert required_title in actual_titles, (
                f"strategic_themes: expected a theme titled {required_title!r}, "
                f"got titles {sorted(actual_titles)}"
            )


def _assert_deviation(expected: dict, deviation) -> None:
    for field in ("status", "move_number", "player_color", "played_san", "better_move_san"):
        if field in expected:
            actual_value = getattr(deviation, field)
            assert actual_value == expected[field], (
                f"deviation.{field}: expected {expected[field]!r}, got {actual_value!r}"
            )


def assert_tactics_agent_expectations(expected: dict, report: TacticsReport) -> None:
    if "minimum_critical_mistakes" in expected:
        assert len(report.crucial_mistakes) >= expected["minimum_critical_mistakes"], (
            f"crucial_mistakes: expected >= {expected['minimum_critical_mistakes']}, "
            f"got {len(report.crucial_mistakes)}"
        )

    if "maximum_critical_mistakes" in expected:
        assert len(report.crucial_mistakes) <= expected["maximum_critical_mistakes"], (
            f"crucial_mistakes: expected <= {expected['maximum_critical_mistakes']}, "
            f"got {len(report.crucial_mistakes)}"
        )

    if "maximum_cp_loss_any_mistake" in expected:
        for lesson in report.crucial_mistakes:
            assert lesson.cp_loss <= expected["maximum_cp_loss_any_mistake"], (
                f"crucial_mistakes: move {lesson.move_number} ({lesson.player_color}) "
                f"cp_loss {lesson.cp_loss} exceeds maximum "
                f"{expected['maximum_cp_loss_any_mistake']}"
            )

    if "required_mistakes" in expected:
        for required in expected["required_mistakes"]:
            match = next(
                (
                    lesson
                    for lesson in report.crucial_mistakes
                    if _matches_required_mistake(required, lesson)
                ),
                None,
            )
            actual_lessons = [
                (lesson.move_number, lesson.player_color, lesson.category, lesson.motif, lesson.cp_loss)
                for lesson in report.crucial_mistakes
            ]
            assert match is not None, (
                f"crucial_mistakes: no lesson matched required spec {required!r} "
                f"(actual lessons: {actual_lessons})"
            )


def _matches_required_mistake(required: dict, lesson) -> bool:
    if "move_number" in required and lesson.move_number != required["move_number"]:
        return False
    if "player_color" in required and lesson.player_color != required["player_color"]:
        return False
    if "category" in required and lesson.category != required["category"]:
        return False
    if "motif" in required and lesson.motif != required["motif"]:
        return False
    if "minimum_cp_loss" in required and lesson.cp_loss < required["minimum_cp_loss"]:
        return False
    return True


def assert_coordinator_expectations(expected: dict, report: CoordinatedReport) -> None:
    if "minimum_lessons" in expected:
        assert len(report.lessons) >= expected["minimum_lessons"], (
            f"lessons: expected >= {expected['minimum_lessons']}, got {len(report.lessons)}"
        )

    if "maximum_lessons" in expected:
        assert len(report.lessons) <= expected["maximum_lessons"], (
            f"lessons: expected <= {expected['maximum_lessons']}, got {len(report.lessons)}"
        )

    if "first_priority_source" in expected:
        assert report.lessons, "lessons: expected at least one lesson to check first_priority_source"
        assert report.lessons[0].source == expected["first_priority_source"], (
            f"lessons[0].source: expected {expected['first_priority_source']!r}, "
            f"got {report.lessons[0].source!r}"
        )

    if "maximum_tactical_habits" in expected:
        assert len(report.tactical_habits) <= expected["maximum_tactical_habits"], (
            f"tactical_habits: expected <= {expected['maximum_tactical_habits']}, "
            f"got {len(report.tactical_habits)}"
        )

    if expected.get("required_tactical_habit_contains"):
        substring = expected["required_tactical_habit_contains"]
        assert any(substring in habit for habit in report.tactical_habits), (
            f"tactical_habits: expected some habit containing {substring!r}, "
            f"got {report.tactical_habits}"
        )


def assert_pipeline_health(expected: dict, report: CoordinatedReport) -> None:
    allowed_warning_codes = set(expected.get("allowed_warning_codes", []))

    for issue in report.input_issues:
        if issue.severity == "error":
            pytest.fail(f"pipeline_health: unexpected fatal input issue: {issue}")

        if issue.severity == "warning" and issue.code not in allowed_warning_codes:
            pytest.fail(
                f"pipeline_health: unexpected warning {issue.code!r} not in "
                f"allowed_warning_codes {sorted(allowed_warning_codes)}: {issue}"
            )


# --------------------------------------------------------------------------
# The test
# --------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("case_dir", discover_cases(), ids=lambda case_dir: case_dir.name)
async def test_case(case_dir: Path, opening_deps: OpeningDeps) -> None:
    expected = json.loads((case_dir / "expected.json").read_text())
    pgn_text = (case_dir / "game.pgn").read_text()

    result = await run_coaching_pipeline(pgn_text, opening_deps)

    assert_pipeline_health(expected.get("pipeline_health", {}), result.coordinated)

    if "opening_agent" in expected:
        assert_opening_agent_expectations(expected["opening_agent"], result.opening)

    if "tactics_agent" in expected:
        assert_tactics_agent_expectations(expected["tactics_agent"], result.tactics)

    if "coordinator" in expected:
        assert_coordinator_expectations(expected["coordinator"], result.coordinated)
