from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


DATASET_COLUMNS = [
    "game_id",
    "turn_no",
    "player_id",
    "rows",
    "cols",
    "max_players",
    "first_row",
    "first_col",
    "second_row",
    "second_col",
    "response_ms",
    "matched_pairs_before",
    "matched_pairs_after",
    "cards_remaining_before",
    "board_progress_pct_before",
    "player_score_before",
    "player_moves_before",
    "matched",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export turn-level ML dataset for match prediction."
    )
    parser.add_argument(
        "--output",
        default="dataset_turn_match_prediction.csv",
        help="CSV output path. Defaults to dataset_turn_match_prediction.csv",
    )
    return parser.parse_args()


def fetch_rows(dsn: str) -> list[dict[str, Any]]:
    query = """
        SELECT
            t.game_id::text AS game_id,
            t.turn_no,
            t.player_id::text AS player_id,
            g.rows,
            g.cols,
            g.max_players,
            t.first_row,
            t.first_col,
            t.second_row,
            t.second_col,
            t.response_ms,
            t.matched_pairs_before,
            t.matched_pairs_after,
            t.cards_remaining_before,
            t.board_progress_pct_before,
            t.player_score_before,
            t.player_moves_before,
            t.matched
        FROM turns t
        JOIN games g ON g.game_id = t.game_id
        ORDER BY t.game_id, t.turn_no
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query)
            return list(cur.fetchall())


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in DATASET_COLUMNS})


def _csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    return value


def main() -> int:
    load_dotenv()
    args = parse_args()
    dsn = os.getenv("MEMORY_DB_DSN")
    if not dsn:
        print("ERROR: MEMORY_DB_DSN is not configured.", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    rows = fetch_rows(dsn)
    write_csv(rows, output_path)
    print(f"Exported {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
