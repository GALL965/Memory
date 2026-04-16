from __future__ import annotations

import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
import time

import psycopg


@dataclass(frozen=True, slots=True)
class GameRow:
    game_id: str
    started_at: datetime | None
    ended_at: datetime | None
    rows: int
    cols: int
    max_players: int
    finished: bool


@dataclass(frozen=True, slots=True)
class PlayerRow:
    player_id: str
    name: str
    score: int
    moves: int
    avg_response_ms: float
    total_response_ms: float


class PostgresStore:
    """PostgreSQL persistence for games, players and moves."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection:
        # When running under docker-compose, Postgres may take a few seconds to accept TCP.
        last_exc: Exception | None = None
        for attempt in range(1, 31):
            try:
                return psycopg.connect(self._dsn, autocommit=True)
            except psycopg.OperationalError as exc:
                last_exc = exc
                time.sleep(min(0.2 * attempt, 2.0))
        assert last_exc is not None
        raise last_exc

    def ensure_schema(self) -> None:
        schema_path = pathlib.Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.execute(sql)

    def create_game(
        self,
        game_id: str,
        rows: int,
        cols: int,
        max_players: int,
        mismatch_hide_delay_ms: int,
    ) -> None:
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO games(game_id, started_at, ended_at, rows, cols, max_players, mismatch_hide_delay_ms, finished)
                VALUES (%s, NULL, NULL, %s, %s, %s, %s, FALSE)
                ON CONFLICT (game_id) DO NOTHING
                """,
                (gid, rows, cols, max_players, mismatch_hide_delay_ms),
            )

    def mark_game_started(self, game_id: str) -> None:
        now = datetime.now(timezone.utc)
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            conn.execute(
                "UPDATE games SET started_at=%s WHERE game_id=%s",
                (now, gid),
            )

    def upsert_player(self, game_id: str, player_id: str, name: str) -> None:
        gid = uuid.UUID(game_id)
        pid = uuid.UUID(player_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO game_players(game_id, player_id, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (game_id, player_id) DO UPDATE SET name = EXCLUDED.name
                """,
                (gid, pid, name),
            )

    def record_move(
        self,
        game_id: str,
        player_id: str,
        seq: int,
        row: int,
        col: int,
        selection_index: int,
        result: str,
    ) -> None:
        gid = uuid.UUID(game_id)
        pid = uuid.UUID(player_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO moves(game_id, player_id, seq, row, col, selection_index, result)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (gid, pid, seq, row, col, selection_index, result),
            )

    def record_turn(
        self,
        game_id: str,
        player_id: str,
        turn_no: int,
        response_ms: float,
        matched: bool,
    ) -> None:
        gid = uuid.UUID(game_id)
        pid = uuid.UUID(player_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO turns(game_id, player_id, turn_no, response_ms, matched)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (gid, pid, turn_no, response_ms, matched),
            )

    def finalize_players(self, game_id: str, players: list[PlayerRow]) -> None:
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            for p in players:
                conn.execute(
                    """
                    UPDATE game_players
                    SET score=%s, moves=%s, avg_response_ms=%s, total_response_ms=%s
                    WHERE game_id=%s AND player_id=%s
                    """,
                    (
                        p.score,
                        p.moves,
                        p.avg_response_ms,
                        p.total_response_ms,
                        gid,
                        uuid.UUID(p.player_id),
                    ),
                )

    def mark_game_finished(self, game_id: str) -> None:
        now = datetime.now(timezone.utc)
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            conn.execute(
                "UPDATE games SET ended_at=%s, finished=TRUE WHERE game_id=%s",
                (now, gid),
            )

    def list_games(self, limit: int) -> list[GameRow]:
        limit = max(1, min(limit, 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT game_id, started_at, ended_at, rows, cols, max_players, finished
                FROM games
                ORDER BY started_at DESC NULLS LAST
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [
            GameRow(
                game_id=str(r[0]),
                started_at=r[1],
                ended_at=r[2],
                rows=int(r[3]),
                cols=int(r[4]),
                max_players=int(r[5]),
                finished=bool(r[6]),
            )
            for r in rows
        ]

    def get_game(self, game_id: str) -> GameRow | None:
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT game_id, started_at, ended_at, rows, cols, max_players, finished
                FROM games
                WHERE game_id=%s
                """,
                (gid,),
            ).fetchone()
        if row is None:
            return None
        return GameRow(
            game_id=str(row[0]),
            started_at=row[1],
            ended_at=row[2],
            rows=int(row[3]),
            cols=int(row[4]),
            max_players=int(row[5]),
            finished=bool(row[6]),
        )

    def get_players(self, game_id: str) -> list[PlayerRow]:
        gid = uuid.UUID(game_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT player_id, name, score, moves, avg_response_ms, total_response_ms
                FROM game_players
                WHERE game_id=%s
                ORDER BY score DESC, name ASC
                """,
                (gid,),
            ).fetchall()
        return [
            PlayerRow(
                player_id=str(r[0]),
                name=str(r[1]),
                score=int(r[2]),
                moves=int(r[3]),
                avg_response_ms=float(r[4]),
                total_response_ms=float(r[5]),
            )
            for r in rows
        ]
