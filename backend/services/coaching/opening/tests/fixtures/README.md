# Fixtures

`najdorf_deviation.pgn` is a test game: follows the Najdorf main line
through move 6, then plays `7...h6` instead of theory's top choice
`7...Be7`. Used by `test_graph.py` together with a fake
`OpeningDeviationService` (see that file) that returns canned
classifications for this exact line -- no real Polyglot book or live
Lichess Explorer call needed.
