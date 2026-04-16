from __future__ import annotations

import os
import sys

# Allow running as: python clients/console/main.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import threading
import time

import grpc

from shared.client_core import (
    ClientState,
    ServerAddress,
    create_stub,
    render_board,
    render_scoreboard,
)
from shared.grpc import memory_pb2


def _clear_screen() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def listen_updates(stub, player_id: str, state: ClientState, stop: threading.Event) -> None:
    try:
        for update in stub.SubscribeToUpdates(memory_pb2.SubscribeRequest(player_id=player_id)):
            if stop.is_set():
                return
            state.update(update.state)
            _clear_screen()
            snapshot = state.snapshot()
            if snapshot is None:
                continue
            print(render_board(snapshot))
            print()
            print(render_scoreboard(snapshot))
            print(f"Turn: {snapshot.current_turn_player_id} | You: {player_id}")
            print(snapshot.message)
    except grpc.RpcError as exc:
        print(f"[updates] stream ended: {exc.code()} {exc.details()}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Memory Match gRPC client (console)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=50051)
    p.add_argument("--name", required=True)
    return p.parse_args()


def _read_pos(prompt: str) -> tuple[int, int]:
    raw = input(prompt).strip()
    parts = raw.split()
    if len(parts) != 2:
        raise ValueError("Enter: <row> <col>")
    return int(parts[0]), int(parts[1])


def _is_valid_local(snapshot: memory_pb2.BoardState, row: int, col: int) -> tuple[bool, str]:
    if row < 0 or col < 0 or row >= snapshot.board.rows or col >= snapshot.board.cols:
        return False, "Out of bounds"
    cell_map = {(c.row, c.col): c for c in snapshot.board.cells}
    cell = cell_map[(row, col)]
    if cell.state == memory_pb2.MATCHED:
        return False, "Card already matched"
    if cell.state == memory_pb2.REVEALED:
        return False, "Card already revealed"
    return True, ""


def main() -> None:
    args = parse_args()
    addr = ServerAddress(args.host, args.port)
    channel, stub = create_stub(addr)

    join = stub.JoinGame(memory_pb2.JoinGameRequest(player_name=args.name))
    player_id = join.player_id
    local_state = ClientState(player_id)
    local_state.update(join.state)

    stop = threading.Event()
    t = threading.Thread(
        target=listen_updates,
        args=(stub, player_id, local_state, stop),
        daemon=True,
    )
    t.start()

    try:
        print(f"Joined as {args.name} ({player_id})")
        print("Waiting for game start...")
        local_state.game_started.wait()

        while not local_state.game_over.is_set():
            local_state.my_turn.wait(timeout=0.5)
            if not local_state.my_turn.is_set():
                continue

            snapshot = local_state.snapshot()
            if snapshot is None:
                time.sleep(0.1)
                continue

            print("\nYour turn. Pick two cards using: row col")
            # First pick
            while True:
                try:
                    r1, c1 = _read_pos("First: ")
                except Exception as exc:  # noqa: BLE001
                    print(exc)
                    continue
                snapshot = local_state.snapshot()
                if snapshot is not None:
                    ok_local, why = _is_valid_local(snapshot, r1, c1)
                    if not ok_local:
                        print(why)
                        continue
                resp1 = stub.PlayMove(memory_pb2.PlayMoveRequest(player_id=player_id, row=r1, col=c1))
                if resp1.ok:
                    break
                print(resp1.message)

            # Second pick
            while True:
                try:
                    r2, c2 = _read_pos("Second: ")
                except Exception as exc:  # noqa: BLE001
                    print(exc)
                    continue
                snapshot = local_state.snapshot()
                if snapshot is not None:
                    ok_local, why = _is_valid_local(snapshot, r2, c2)
                    if not ok_local:
                        print(why)
                        continue
                resp2 = stub.PlayMove(memory_pb2.PlayMoveRequest(player_id=player_id, row=r2, col=c2))
                if resp2.ok:
                    break
                print(resp2.message)

            # Turn ends; wait for TURN_CHANGED update.
            time.sleep(0.1)
    finally:
        stop.set()
        channel.close()


if __name__ == "__main__":
    main()
