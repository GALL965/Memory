from __future__ import annotations

import os
import sys

# Allow running as: python clients/gui/main.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import queue
import threading
import tkinter as tk
from tkinter import ttk

import grpc

from shared.client_core import ClientState, ServerAddress, create_stub, render_scoreboard
from shared.grpc import memory_pb2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Memory Match gRPC client (Tkinter GUI)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=50051)
    p.add_argument("--name", required=True)
    return p.parse_args()


class GuiApp:
    def __init__(self, root: tk.Tk, stub, player_id: str, state: ClientState):
        self.root = root
        self.stub = stub
        self.player_id = player_id
        self.state = state

        self.update_queue: queue.Queue[memory_pb2.BoardState] = queue.Queue()

        self.status = tk.StringVar(value="Waiting...")

        header = ttk.Frame(root)
        header.pack(fill="x", padx=8, pady=6)
        ttk.Label(header, textvariable=self.status).pack(anchor="w")

        main = ttk.Frame(root)
        main.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(main)
        right.pack(side="right", fill="y")

        self.board_frame = ttk.Frame(left)
        self.board_frame.pack()

        ttk.Label(right, text="Scoreboard").pack(anchor="w")
        self.score_table = ttk.Treeview(
            right,
            columns=("score", "moves", "avg_ms"),
            show="headings",
            height=8,
        )
        self.score_table.heading("score", text="score")
        self.score_table.heading("moves", text="moves")
        self.score_table.heading("avg_ms", text="avg_ms")
        self.score_table.column("score", width=60, anchor="e")
        self.score_table.column("moves", width=60, anchor="e")
        self.score_table.column("avg_ms", width=70, anchor="e")
        self.score_table.pack(fill="y", expand=False, pady=(4, 0))

        ttk.Label(right, text="Players").pack(anchor="w", pady=(10, 0))
        self.players_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.players_var, justify="left").pack(anchor="w")
        self.buttons: dict[tuple[int, int], tk.Button] = {}

        self.root.after(100, self._process_updates)

    def start_listener(self) -> None:
        t = threading.Thread(target=self._listen_updates, daemon=True)
        t.start()

    def _listen_updates(self) -> None:
        try:
            for update in self.stub.SubscribeToUpdates(memory_pb2.SubscribeRequest(player_id=self.player_id)):
                self.state.update(update.state)
                self.update_queue.put(update.state)
        except grpc.RpcError as exc:
            self.update_queue.put(
                memory_pb2.BoardState(message=f"Stream ended: {exc.code()} {exc.details()}")
            )

    def _ensure_grid(self, rows: int, cols: int) -> None:
        if self.buttons:
            return
        for r in range(rows):
            for c in range(cols):
                btn = ttk.Button(
                    self.board_frame,
                    text="🂠",
                    command=lambda rr=r, cc=c: self._on_pick(rr, cc),
                )
                btn.grid(row=r, column=c, padx=2, pady=2)
                self.buttons[(r, c)] = btn

    def _refresh_interaction(self, st: memory_pb2.BoardState) -> None:
        # Enable buttons only if it's my turn and cell is HIDDEN.
        my_turn = st.game_started and (not st.game_over) and st.current_turn_player_id == self.player_id
        cell_map = {(c.row, c.col): c for c in st.board.cells}
        for (r, c), btn in self.buttons.items():
            cell = cell_map[(r, c)]
            if not my_turn:
                btn.state(["disabled"])
                continue
            if cell.state == memory_pb2.HIDDEN:
                btn.state(["!disabled"])
            else:
                btn.state(["disabled"])

    def _on_pick(self, row: int, col: int) -> None:
        snapshot = self.state.snapshot()
        if snapshot is None or not snapshot.game_started:
            self.status.set("Game not started")
            return
        if snapshot.game_over:
            self.status.set("Game over")
            return
        if snapshot.current_turn_player_id != self.player_id:
            self.status.set("Not your turn")
            return

        if row < 0 or col < 0 or row >= snapshot.board.rows or col >= snapshot.board.cols:
            self.status.set("Out of bounds")
            return
        cell_map = {(c.row, c.col): c for c in snapshot.board.cells}
        cell = cell_map[(row, col)]
        if cell.state == memory_pb2.MATCHED:
            self.status.set("Card already matched")
            return
        if cell.state == memory_pb2.REVEALED:
            self.status.set("Card already revealed")
            return

        resp = self.stub.PlayMove(memory_pb2.PlayMoveRequest(player_id=self.player_id, row=row, col=col))
        if not resp.ok:
            self.status.set(resp.message)

    def _process_updates(self) -> None:
        try:
            while True:
                st = self.update_queue.get_nowait()
                if st.board.rows and st.board.cols:
                    self._ensure_grid(st.board.rows, st.board.cols)
                    cell_map = {(c.row, c.col): c for c in st.board.cells}
                    for (r, c), btn in self.buttons.items():
                        cell = cell_map[(r, c)]
                        if cell.state == memory_pb2.HIDDEN:
                            btn.configure(text="🂠")
                        elif cell.state == memory_pb2.REVEALED:
                            btn.configure(text=cell.emoji or "?")
                        elif cell.state == memory_pb2.MATCHED:
                            btn.configure(text=cell.emoji or "✓")
                        else:
                            btn.configure(text="?")

                    self._refresh_interaction(st)

                if st.players:
                    # Update scoreboard table.
                    for item in self.score_table.get_children():
                        self.score_table.delete(item)
                    for p in st.players:
                        self.score_table.insert(
                            "",
                            "end",
                            values=(p.score, p.moves, f"{p.avg_response_ms:.1f}"),
                            text=p.name,
                        )
                    self.players_var.set("\n".join([f"{p.name} ({p.player_id[:8]})" for p in st.players]))

                msg = st.message or ""
                turn = st.current_turn_player_id or ""
                you = self.player_id[:8]
                self.status.set(f"Turn: {turn[:8]} | You: {you} | {msg}")
        except queue.Empty:
            pass
        self.root.after(100, self._process_updates)


def main() -> None:
    args = parse_args()
    addr = ServerAddress(args.host, args.port)
    channel, stub = create_stub(addr)
    join = stub.JoinGame(memory_pb2.JoinGameRequest(player_name=args.name))

    player_id = join.player_id
    state = ClientState(player_id)
    state.update(join.state)

    root = tk.Tk()
    root.title(f"Memory - {args.name} ({player_id[:8]})")
    app = GuiApp(root, stub, player_id, state)
    app.start_listener()
    try:
        root.mainloop()
    finally:
        channel.close()


if __name__ == "__main__":
    main()
