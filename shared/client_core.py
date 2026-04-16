from __future__ import annotations

import threading
from dataclasses import dataclass

import grpc

from shared.grpc import memory_pb2, memory_pb2_grpc


@dataclass(slots=True)
class ServerAddress:
    host: str
    port: int

    def target(self) -> str:
        return f"{self.host}:{self.port}"


class ClientState:
    """Thread-safe snapshot of the latest BoardState."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        self._lock = threading.Lock()
        self._state: memory_pb2.BoardState | None = None

        self.game_started = threading.Event()
        self.game_over = threading.Event()
        self.my_turn = threading.Event()

    def update(self, state: memory_pb2.BoardState) -> None:
        with self._lock:
            self._state = state

        if state.game_started:
            self.game_started.set()
        if state.game_over:
            self.game_over.set()

        if state.current_turn_player_id == self.player_id and state.game_started and not state.game_over:
            self.my_turn.set()
        else:
            self.my_turn.clear()

    def snapshot(self) -> memory_pb2.BoardState | None:
        with self._lock:
            return self._state


def create_stub(addr: ServerAddress) -> tuple[grpc.Channel, memory_pb2_grpc.MemoryGameServiceStub]:
    channel = grpc.insecure_channel(addr.target())
    stub = memory_pb2_grpc.MemoryGameServiceStub(channel)
    return channel, stub


def board_cell_map(state: memory_pb2.BoardState) -> dict[tuple[int, int], memory_pb2.CellView]:
    return {(c.row, c.col): c for c in state.board.cells}


def render_board(state: memory_pb2.BoardState) -> str:
    cell_map = board_cell_map(state)
    lines: list[str] = []

    header = "    " + " ".join([f"{c:2d}" for c in range(state.board.cols)])
    lines.append(header)

    for row in range(state.board.rows):
        row_items = []
        for col in range(state.board.cols):
            cell = cell_map[(row, col)]
            if cell.state == memory_pb2.HIDDEN:
                row_items.append("🂠")
            elif cell.state == memory_pb2.REVEALED:
                row_items.append(cell.emoji or "?")
            elif cell.state == memory_pb2.MATCHED:
                row_items.append(cell.emoji or "✓")
            else:
                row_items.append("?")
        lines.append(f"{row:2d}: " + "  ".join(row_items))

    return "\n".join(lines)


def render_scoreboard(state: memory_pb2.BoardState) -> str:
    parts = []
    for p in state.players:
        parts.append(f"{p.name} score={p.score} moves={p.moves} avg_ms={p.avg_response_ms:.1f}")
    return " | ".join(parts)
