# gm_game_01 — observed real run

Real game: Caruana vs. Firouzja, 2024 Champions Chess Tour (Chess.com
export, with `%clk` clock comments and an embedded side-variation in
parens after move 9). `game.pgn` was not modified for this run.

## PGN edge case confirmed: side-variation is correctly skipped

`extract_moves()` found **17 plies** — exactly the actual mainline (moves
1–9), stopping at White's `9. Rxa7`. The parenthetical
`(9. Rxa7 Rxa7 10. c7 e6 11. c8=Q+ ...)` — chess.com's annotation showing
why Black's position was lost, not moves actually played — is correctly
excluded. `chess.pgn.read_game().mainline_moves()` only follows the
actually-played line; bracketed/parenthetical side-variations are ignored
by design, same mechanism already relied on for the `%clk` comments.

## Your actual question: how does the pipeline interpret "brilliant" moves?

**Short answer: it doesn't — brilliant/good moves never reach any exposed
report at all.** Two separate things going on here:

1. `services/stockfish.py::cp_loss_to_quality` *does* have a `"brilliant"`
   tier (`cp_loss < 0`, i.e. the played move scored better than the
   engine's own "best move" search — a search-inconsistency artifact
   between two different-purpose Stockfish calls, not a real
   "genius sacrifice" detector like chess.com's badge). But this label
   only ever lives on the intermediate `AnnotatedMove`/raw
   `annotate_moves()` dict — **no `brilliant` example showed up in this
   game either way** (see the full quality table below — nothing scored
   cp_loss < 0 here).
2. Even when a move *does* get labeled `"good"` or `"brilliant"`,
   `services/coaching/tactics/pipeline/candidate_selection.py`'s
   `select_candidates` only keeps moves with `quality in {"mistake",
   "blunder"}` (or cp_loss ≥ 100) as tactical candidates. Anything better
   than "mistake" is filtered out before a `TacticalLesson` is ever built
   — so `TacticsReport`/`OpeningReport`/`CoordinatedReport` structurally
   **cannot** surface a "this was brilliant" note today. It's not a bug in
   this game's result, it's a scope limitation: the whole pipeline is
   built to find and explain *mistakes*, not to praise good moves.

## Raw per-move quality (services.stockfish.annotate_moves — NOT exposed on any report)

| move | color | played | cp_loss | quality |
|---|---|---|---|---|
| 1 | white | c4   | 27  | mistake |
| 1 | black | c6   | 30  | mistake |
| 2 | white | Nf3  | 4   | good |
| 2 | black | d5   | 0   | good |
| 3 | white | g3   | 14  | inaccuracy |
| 3 | black | Bg4  | 5   | good |
| 4 | white | Ne5  | 0   | good |
| 4 | black | Bf5  | 0   | good |
| 5 | white | Qb3  | 0   | good |
| 5 | black | Qb6  | 0   | good |
| 6 | white | cxd5 | 0   | good |
| 6 | black | Qxb3 | 0   | good |
| 7 | white | axb3 | 0   | good |
| 7 | black | Be4  | 0   | good |
| 8 | white | dxc6 | 0   | good |
| **8** | **black** | **Bxh1** | **377** | **blunder** |
| 9 | white | Rxa7 | 0   | good |

`8...Bxh1` — the move that *looks* spectacular (grabbing a rook on the
far side of the board) — is the only real mistake either side made,
scored as a **blunder**, not a brilliancy. This actually matches how this
game is discussed in real commentary: grabbing the rook wins material but
ignores that Black's whole position is already collapsing (White's
c-pawn is running toward promotion) — the engine's suggested `Nxc6`
instead. This is the system working as intended, not a misfire.

## Opening agent

- eco: `A11`, name: `English Opening`, variation: `Caro-Kann Defensive System`
- deviation: `deviated` at move 1/white (`c4`), better `e4` — same fixture-book-coverage caveat as always (this book only knows the one Najdorf line; treat this deviation as an artifact, not a judgment on `1. c4`)
- critical_mistakes (2): move 7/black `Be4` (85cp, mistake), move 8/black `Bxh1` (359cp, **blunder**)

## Tactics agent

3 crucial_mistakes found:

| move | color | played | better | cp_loss | category | motif |
|---|---|---|---|---|---|---|
| 8 | black | Bxh1 | Nxc6 | 377 | offensive | missed_capture |
| 7 | black | Be4  | Bxb1 | 76  | offensive | missed_capture |
| 1 | black | c6   | e5   | 32  | mixed | calculation_error |

⚠️ **Live example of the category/explanation-text mismatch flagged
earlier this session**: move 8's `category` is correctly `"offensive"`
(the best move `Nxc6` is a capture), but the `explanation` text reads:
*"Bxh1 left your pawn on f7 available to an immediate capture. **The
tactical error is defensive**..."* — the label says offensive, the prose
says defensive. Same root cause as the `opening_and_tactics_02` case:
`select_motif` and `_lesson_explanation` in
`report/tactical_rules.py`/`report/lesson_builder.py` are two independent
decision cascades over the same features and can disagree. Not something
to work around in `expected.json` — just don't assert on `explanation`
text, per the project's own rule, and know this is a known, already-
discussed gap, not a new one.

## Coordinator

3 ranked lessons, no truncation:

| rank | move | color | source | cp_loss |
|---|---|---|---|---|
| 1 | 8 | black | both    | 359 |
| 2 | 7 | black | both    | 85  |
| 3 | 1 | black | tactics | 32  |

- Both agents independently flagged moves 7 and 8 (`source="both"`) —
  another real example of cp_loss differing slightly between the two
  agents' independent Stockfish calls (opening: 359/85, tactics: 377/76)
  — coordinator keeps the opening agent's value as canonical per
  `coordinator/merging.py`.
- `tactical_habits`: `[]`. `input_issues`: `[]` on all three reports.
