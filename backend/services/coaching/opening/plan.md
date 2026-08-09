# Opening Agent

# Input
- PGN
- Current position (FEN)
- User color
- Opening database

# Output
- Opening name (identify opening)
- Where user left theory (deviations)
- Critical mistakes in opening
- Better move(s) + better lines 
- Strategic themes (examples: center development and minor piece development)
-Typical Middlegame plans 
-Model and Example Games (with their opening) (with high rated players) 


# Example

Opening

* Sicilian Defense
* Najdorf Variation
* ECO: B90

Theory status

* Followed the main line until move 6
* Left established theory on move 7

Deviation

* Played 7...h6 instead of the main line 7...Be7
* Delayed kingside development
* Postponed castling

Critical mistakes

* Spent a tempo on a pawn move before completing development
* Allowed White to strengthen central control
* Reduced flexibility for future piece coordination

Better moves

* 7...Be7
* Develop the dark-squared bishop before making additional pawn moves

Better line

* 7...Be7
* 8. O-O O-O
* 9. Be3 Nc6
* 10. f4

Strategic themes

* Contest White's central pawn duo with ...e5 or ...d5
* Prioritize rapid minor piece development
* Castle early and connect the rooks
* Expand on the queenside with ...b5
* Pressure the c-file
* Control the d5 square

Typical middlegame plans

Black

* Expand with ...b5
* Pressure the c-file with the rooks
* Challenge the center with ...e5 or ...d5
* Create queenside counterplay

White

* Expand on the kingside with f4
* Maintain central space
* Launch a kingside attack
* Restrict Black's queenside play

Model games

* Garry Kasparov vs Viswanathan Anand (1995) — Sicilian Defense: Najdorf Variation
* Magnus Carlsen vs Hikaru Nakamura (2019) — Sicilian Defense: Najdorf Variation
* Bobby Fischer vs Bent Larsen (1971) — Sicilian Defense: Najdorf Variation


# Dependencies
- Opening DB
- Stockfish
- LLM


# Pipeline
Position
    ↓
Identify opening
    ↓
Find theory
    ↓
Compare game to theory
    ↓
Evaluate deviations
    ↓
Generate coaching