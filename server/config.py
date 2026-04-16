from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int

    rows: int
    cols: int
    max_players: int
    mismatch_hide_delay_ms: int

    db_dsn: str | None


def load_config() -> ServerConfig:
    host = os.getenv("MEMORY_HOST", "0.0.0.0")
    port = int(os.getenv("MEMORY_PORT", "50051"))

    rows = int(os.getenv("MEMORY_ROWS", "4"))
    cols = int(os.getenv("MEMORY_COLS", "4"))
    max_players = int(os.getenv("MEMORY_PLAYERS", "2"))
    mismatch_hide_delay_ms = int(os.getenv("MEMORY_MISMATCH_DELAY_MS", "1000"))

    db_dsn = os.getenv("MEMORY_DB_DSN")
    return ServerConfig(
        host=host,
        port=port,
        rows=rows,
        cols=cols,
        max_players=max_players,
        mismatch_hide_delay_ms=mismatch_hide_delay_ms,
        db_dsn=db_dsn,
    )
