"""
Generates eco/data/eco_index.json from the real, comprehensive ECO dataset
at lichess-org/chess-openings (CC0 Public Domain -- no attribution
required, verified directly against the live repo before this script was
written).

This is a committed, reproducible, run-on-demand build step -- not part of
the request-time runtime. `eco_index.py`'s loading/lookup code needs no
changes: it already expects exactly the
`{move_prefix_uci: {"eco", "name", "variation"}}` shape this script emits,
regardless of how many entries there are.

Network access is required to run this script (it fetches the source
TSVs fresh each time -- they are not cached/committed), but never at
app-request time; the generated eco_index.json is static.

Run with:

    python -m services.coaching.opening.eco.build_eco_index
"""

from __future__ import annotations

import csv
import io
import json
import logging
import urllib.request
from pathlib import Path

import chess.pgn

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

SOURCE_URL_TEMPLATE = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/{volume}.tsv"
VOLUMES = ("a", "b", "c", "d", "e")

OUTPUT_PATH = Path(__file__).parent / "data" / "eco_index.json"


def _fetch_tsv_rows(volume: str) -> list[dict[str, str]]:
    url = SOURCE_URL_TEMPLATE.format(volume=volume)
    logger.info("Fetching %s", url)

    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 -- fixed, trusted host
        text = response.read().decode("utf-8")

    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def _split_name_and_variation(raw_name: str) -> tuple[str, str | None]:
    """"Sicilian Defense: Najdorf Variation, English Attack" ->
    ("Sicilian Defense", "Najdorf Variation, English Attack")."""
    if ":" not in raw_name:
        return raw_name.strip(), None

    name, variation = raw_name.split(":", 1)
    return name.strip(), variation.strip() or None


def _pgn_to_uci_prefix(pgn_movetext: str) -> str | None:
    """Numbered SAN movetext -> space-joined UCI move-prefix key.

    Uses chess.pgn's own tokenizer/parser (matches services/pgn_utils.py's
    approach elsewhere in this codebase) rather than hand-splitting move
    numbers -- robust to captures, checks, castling, etc. Returns None
    (skip the row) if the movetext doesn't parse cleanly.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_movetext))

    if game is None or game.errors:
        return None

    uci_moves = [move.uci() for move in game.mainline_moves()]

    if not uci_moves:
        return None

    return " ".join(uci_moves)


def build() -> dict[str, dict[str, str | None]]:
    index: dict[str, dict[str, str | None]] = {}
    total_rows = 0
    skipped_rows = 0

    for volume in VOLUMES:
        rows = _fetch_tsv_rows(volume)
        total_rows += len(rows)

        for row in rows:
            prefix = _pgn_to_uci_prefix(row["pgn"])

            if prefix is None:
                skipped_rows += 1
                logger.warning("Skipping unparseable row: %s / %s", row.get("eco"), row.get("name"))
                continue

            name, variation = _split_name_and_variation(row["name"])
            index[prefix] = {"eco": row["eco"], "name": name, "variation": variation}

    logger.info(
        "Processed %d source rows -> %d entries (%d skipped, %d overwritten/duplicate prefixes).",
        total_rows,
        len(index),
        skipped_rows,
        total_rows - skipped_rows - len(index),
    )
    return index


def main() -> None:
    index = build()

    output = {
        "_source": "https://github.com/lichess-org/chess-openings (CC0 Public Domain)",
        "_regenerate": "python -m services.coaching.opening.eco.build_eco_index",
        **index,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as output_file:
        json.dump(output, output_file, indent=2, sort_keys=True)

    logger.info("Wrote %d entries to %s", len(index), OUTPUT_PATH)


if __name__ == "__main__":
    main()
