from __future__ import annotations

import os
import sys

# Allow running as: python server/main.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

from server.config import load_config
from server.domain.game_state import GameConfig
from server.game_manager import GameManager
from server.service import create_grpc_server
from server.storage.postgres_store import PostgresStore


def main() -> None:
    load_dotenv()
    cfg = load_config()

    store = PostgresStore(cfg.db_dsn) if cfg.db_dsn else None

    game_cfg = GameConfig(
        rows=cfg.rows,
        cols=cfg.cols,
        max_players=cfg.max_players,
        mismatch_hide_delay_ms=cfg.mismatch_hide_delay_ms,
    )
    manager = GameManager(game_cfg, store=store)
    server = create_grpc_server(manager, store=store)
    server.add_insecure_port(f"{cfg.host}:{cfg.port}")
    server.start()
    print(f"Memory gRPC server listening on {cfg.host}:{cfg.port}")
    print(f"Board: {cfg.rows}x{cfg.cols} | players: {cfg.max_players}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
