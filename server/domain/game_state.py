from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .board import Board
from .types import Position


class Phase(Enum):
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    IN_TURN = "IN_TURN"
    RESOLVING_MISMATCH = "RESOLVING_MISMATCH"
    GAME_OVER = "GAME_OVER"


@dataclass(slots=True)
class PlayerState:
    player_id: str
    name: str
    score: int = 0
    moves: int = 0
    response_times_ms: list[float] = field(default_factory=list)

    def avg_response_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        return sum(self.response_times_ms) / len(self.response_times_ms)

    def total_response_ms(self) -> float:
        return sum(self.response_times_ms)


@dataclass(slots=True)
class GameConfig:
    rows: int
    cols: int
    max_players: int
    mismatch_hide_delay_ms: int


@dataclass(slots=True)
class TurnResult:
    match: bool
    pos1: Position
    pos2: Position
    emoji1: str
    emoji2: str
    response_ms: float
    turn_no: int


class GameState:
    """In-memory state and rules for a single match."""

    def __init__(self, config: GameConfig, board: Board):
        self.config = config
        self.board = board

        self.game_id = str(uuid.uuid4())
        self.lobby_open = True
        self.game_started = False
        self.game_over = False
        self.phase = Phase.WAITING_FOR_PLAYERS

        self.players: dict[str, PlayerState] = {}
        self.turn_order: list[str] = []
        self.current_turn_index = 0

        self._seq = 0
        self._message = "Server ready. Waiting for players..."

        self._turn_started_at = 0.0
        self._first_pick: Position | None = None
        self._turn_no = 0

    @property
    def turn_no(self) -> int:
        return self._turn_no

    @property
    def seq(self) -> int:
        return self._seq

    @property
    def message(self) -> str:
        return self._message

    def bump_seq(self, message: str) -> None:
        self._seq += 1
        self._message = message

    def join_player(self, name: str) -> str:
        if not self.lobby_open:
            raise ValueError("Lobby is closed")
        if not name.strip():
            raise ValueError("Player name cannot be empty")
        if len(self.players) >= self.config.max_players:
            raise ValueError("Game is full")

        player_id = str(uuid.uuid4())
        self.players[player_id] = PlayerState(player_id=player_id, name=name.strip())
        self.turn_order.append(player_id)
        return player_id

    def can_start(self) -> bool:
        return len(self.players) == self.config.max_players

    def start_game(self) -> None:
        if self.game_started:
            return
        if not self.can_start():
            raise ValueError("Not enough players")

        self.game_started = True
        self.lobby_open = False
        self.phase = Phase.IN_TURN
        self.current_turn_index = 0
        self._turn_started_at = time.monotonic()
        self._first_pick = None

    def current_turn_player_id(self) -> str:
        if not self.turn_order:
            return ""
        return self.turn_order[self.current_turn_index]

    def require_turn(self, player_id: str) -> None:
        if player_id != self.current_turn_player_id():
            raise ValueError("Not your turn")

    def is_busy(self) -> bool:
        return self.phase == Phase.RESOLVING_MISMATCH

    def pick(self, player_id: str, pos: Position) -> tuple[str, TurnResult | None, tuple[Position, Position] | None]:
        """Apply a single selection.

        Returns:
          - message: human readable
          - turn_result: present only after second pick
          - mismatch_to_hide: only when mismatch occurs (pos1,pos2)
        """

        if self.game_over:
            raise ValueError("Game is over")
        if not self.game_started:
            raise ValueError("Game has not started")
        if self.is_busy():
            raise ValueError("Resolving previous turn, please wait")
        if player_id not in self.players:
            raise ValueError("Unknown player")

        self.require_turn(player_id)

        if not self.board.in_bounds(pos):
            raise ValueError("Invalid position")
        if self.board.is_matched(pos):
            raise ValueError("Card already matched")
        if self.board.is_revealed(pos):
            raise ValueError("Card already revealed")

        self.players[player_id].moves += 1

        emoji = self.board.reveal(pos)
        if self._first_pick is None:
            self._first_pick = pos
            return (f"First pick: ({pos.row},{pos.col}) {emoji}", None, None)

        pos1 = self._first_pick
        pos2 = pos
        self._first_pick = None

        emoji1 = self.board.emoji_at(pos1)
        emoji2 = self.board.emoji_at(pos2)

        response_ms = (time.monotonic() - self._turn_started_at) * 1000.0
        self.players[player_id].response_times_ms.append(response_ms)

        is_match = emoji1 == emoji2
        if is_match:
            self.board.match(pos1, pos2)
            self.players[player_id].score += 1
            self._turn_no += 1
            turn = TurnResult(
                match=True,
                pos1=pos1,
                pos2=pos2,
                emoji1=emoji1,
                emoji2=emoji2,
                response_ms=response_ms,
                turn_no=self._turn_no,
            )
            return ("Match!", turn, None)

        self._turn_no += 1
        turn = TurnResult(
            match=False,
            pos1=pos1,
            pos2=pos2,
            emoji1=emoji1,
            emoji2=emoji2,
            response_ms=response_ms,
            turn_no=self._turn_no,
        )
        return ("No match.", turn, (pos1, pos2))

    def advance_turn(self) -> None:
        if not self.turn_order:
            return
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        self._turn_started_at = time.monotonic()
        self._first_pick = None

    def set_game_over(self) -> None:
        self.game_over = True
        self.phase = Phase.GAME_OVER
