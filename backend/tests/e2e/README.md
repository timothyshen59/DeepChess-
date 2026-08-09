# E2E coaching-pipeline regression suite

Runs the real, public pipeline (`services/coaching/pipeline.py::run_coaching_pipeline`
— real Stockfish, the committed synthetic Polyglot book fixture, the real
opening/tactics/coordinator graphs) against a real PGN and checks the
result against a **hand-written, manually-reviewed** `expected.json`.

This suite deliberately does **not**:
- compare full generated reports against exact JSON snapshots,
- assert exact natural-language explanation wording,
- treat whatever the agents currently output as ground truth.

## Structure

```
tests/e2e/
├── test_coaching_pipeline.py   # fixtures, discovery, assertion helpers, the one parametrized test
└── cases/
    └── <case_name>/
        ├── game.pgn              # a real (or hand-constructed, clearly-legal) game
        └── expected.json          # manually reviewed, stable behavioral assertions only
```

A case only participates if its directory has **both** `game.pgn` and
`expected.json`. Each shows up as its own pytest ID, e.g.
`test_coaching_pipeline.py::test_case[najdorf_deviation_01]`.

## `expected.json` shape

Every top-level section is optional; a case that only cares about the
opening agent can omit `tactics_agent`/`coordinator` entirely.

```json
{
  "case_id": "najdorf_deviation_01",

  "opening_agent": {
    "eco": "B90",
    "name_contains": "Sicilian",
    "variation_contains": "Najdorf",
    "minimum_matched_plies": 8,
    "deviation": {
      "status": "deviated",
      "move_number": 7,
      "player_color": "black",
      "played_san": "h6",
      "better_move_san": "Be7"
    },
    "minimum_critical_mistakes": 0,
    "required_strategic_theme_titles": ["Development tempo"]
  },

  "tactics_agent": {
    "minimum_critical_mistakes": 1,
    "maximum_critical_mistakes": 4,
    "maximum_cp_loss_any_mistake": 400,
    "required_mistakes": [
      {"move_number": 10, "player_color": "white", "category": "defensive", "motif": "hanging_piece", "minimum_cp_loss": 400}
    ]
  },

  "coordinator": {
    "minimum_lessons": 1,
    "maximum_lessons": 3,
    "first_priority_source": "tactics",
    "maximum_tactical_habits": 3,
    "required_tactical_habit_contains": null
  },

  "pipeline_health": {
    "allowed_warning_codes": []
  }
}
```

Field paths correspond directly to the real Pydantic schemas
(`services/coaching/opening/schemas.py`, `tactics/schemas.py`,
`coordinator/schemas.py`) — see each assertion helper in
`test_coaching_pipeline.py` for exactly what it checks. Note:
`TacticalLesson` has no `severity` field (only `category`/`motif`/`cp_loss`)
— don't try to assert a tactics "severity" the schema doesn't have.

## Adding a case

1. Make a new `cases/<name>/` directory.
2. Add `game.pgn` — a real export or a short, clearly-legal constructed
   position (verify legality with `python-chess` if hand-writing one, not
   by eye).
3. Actually run the pipeline against it once (locally, with Stockfish
   available) and look at the real output before writing `expected.json`
   — don't guess at thresholds blind.
4. Write `expected.json` with only the fields you've reviewed and want to
   lock in. Every skeleton in this repo uses deliberately-impossible
   placeholder values (`"REPLACE_ME"` strings, `999999`/`-1` thresholds) so
   an unedited case always fails loudly instead of silently passing —
   follow that convention for new cases too.

## Known constraints

- **Opening deviation detection defaults to the committed synthetic
  fixture book** (`services/coaching/opening/tests/fixtures/najdorf_seed_book.bin`
  — just the one Najdorf line from `plan.md`'s worked example). Any other
  opening will legitimately show `deviation.status` diverging almost
  immediately, or `"book_unavailable"` — that's expected, not a bug.
  **Set `POLYGLOT_BOOK_PATH`** (same env var the live app's
  `opening_deps.py` reads) to point this suite at a real book instead —
  e.g. a local `performance.bin` — for more meaningful deviation detection
  during local runs. Never rely on this being set: CI has no such file, so
  every case's assertions must still make sense against the default
  fixture book, or be written to tolerate `"book_unavailable"`.
- **`crucial_mistakes`/`critical_mistakes` are capped at 4 each upstream**,
  independent of this suite (by the tactics and opening agents
  themselves). `CoordinatedReport.lessons` is capped at 10.
- **`TacticsReport` never exposes `StrategicFact`/strategic-explanation
  data** — it's computed by the tactics graph but only lives in internal
  graph state, not the public report. Not assertable here today.
- **`services/coaching/pipeline.py` is a thin sequencing module**, not new
  analysis — it just calls the existing opening/tactics/coordinator graphs
  in order. If you need a different orchestration (e.g. skip the
  coordinator), call the individual graphs directly instead of extending
  this function with conditionals.

## Running

```
pytest -m "not e2e"                        # everything else -- fast, no Stockfish, unaffected
pytest -m e2e tests/e2e -v                  # this suite only
STOCKFISH_PATH=/usr/bin/stockfish pytest -m e2e tests/e2e -v   # override the engine path (e.g. in CI)
POLYGLOT_BOOK_PATH=/path/to/performance.bin pytest -m e2e tests/e2e -v   # override the opening book
```

With no usable Stockfish binary reachable, every case in this suite skips
with a clear message instead of erroring.

## CI/CD integration

- `pyproject.toml` already registers the `e2e` marker.
- A CI job needs: a `stockfish` binary on PATH (`apt-get install -y
  stockfish` on Linux, or set `STOCKFISH_PATH` to wherever it's installed),
  then `pytest -m e2e tests/e2e` as its own step, separate from the fast
  `pytest -m "not e2e"` step.
- Per the project's future-testing plan: a faster, frozen-Stockfish-
  annotation tier (skip re-running the engine, feed a saved
  `annotated_moves.json` straight into the tactics graph/coordinator) is
  intentionally **not** built here — only add it if/when it's actually
  needed.
