from __future__ import annotations

import argparse
import os
import sys

import grpc

# Allow running as: python clients/admin/main.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from google.protobuf.json_format import MessageToDict  # noqa: E402

from shared.client_core import ServerAddress, create_stub  # noqa: E402
from shared.grpc import memory_pb2  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Memory Match gRPC admin client")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=50051)

    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List recent games")
    p_list.add_argument("--limit", type=int, default=10)

    p_stats = sub.add_parser("stats", help="Show stats for a game")
    p_stats.add_argument("game_id")

    return p.parse_args()


def main() -> None:
    args = parse_args()
    addr = ServerAddress(args.host, args.port)
    channel, stub = create_stub(addr)

    try:
        if args.cmd == "list":
            resp = stub.ListGames(memory_pb2.ListGamesRequest(limit=args.limit))
            if not resp.games:
                print("No games found (or DB not configured).")
                return
            for g in resp.games:
                print(
                    f"{g.game_id} finished={g.finished} board={g.rows}x{g.cols} players={g.max_players}"
                )

        if args.cmd == "stats":
            resp = stub.GetGameStats(memory_pb2.GetGameStatsRequest(game_id=args.game_id))
            d = MessageToDict(resp, preserving_proto_field_name=True)
            summary = d.get("summary", {})
            print("Summary:")
            for k in ["game_id", "rows", "cols", "max_players", "finished", "started_at", "ended_at"]:
                if k in summary:
                    print(f"- {k}: {summary[k]}")
            print("\nPlayers:")
            for p in d.get("players", []):
                print(
                    f"- {p.get('name')} score={p.get('score')} moves={p.get('moves')} avg_ms={p.get('avg_response_ms')} total_ms={p.get('total_response_ms')}"
                )
    except grpc.RpcError as exc:
        print(f"RPC error: {exc.code()} {exc.details()}")
    finally:
        channel.close()


if __name__ == "__main__":
    main()
