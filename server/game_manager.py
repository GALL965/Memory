from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from server.domain.board import Board
from server.domain.figures import default_emoji_pool
from server.domain.game_state import GameConfig, GameState, Phase, TurnResult
from server.domain.types import Position
from server.grpc_mapping import now_timestamp, state_to_board_state
from server.pubsub import SubscriberHub
from server.stats_report import print_final_stats, summarize_players
from server.storage.postgres_store import PlayerRow, PostgresStore
from shared.grpc import memory_pb2


@dataclass(slots=True)
class MoveOutcome:
    ok: bool
    message: str
    state: memory_pb2.BoardState


class GameManager:
    """Coordinates game state, concurrency and broadcasts."""

    def __init__(self, config: GameConfig, store: PostgresStore | None = None):
        self._lock = threading.Lock()
        board = Board(config.rows, config.cols, default_emoji_pool())
        self._state = GameState(config=config, board=board)

        self._store = store
        if self._store is not None:
            self._store.ensure_schema()
            self._store.create_game(
                game_id=self._state.game_id,
                rows=config.rows,
                cols=config.cols,
                max_players=config.max_players,
                mismatch_hide_delay_ms=config.mismatch_hide_delay_ms,
            )

        self._hub = SubscriberHub()
        self._mismatch_timer: threading.Timer | None = None

    @property
    def state(self) -> GameState:
        return self._state

    def subscribe_queue(self) -> tuple[str, "queue.Queue[memory_pb2.GameUpdate]", memory_pb2.GameUpdate]:
        sub_id, q = self._hub.add()
        with self._lock:
            snapshot = state_to_board_state(self._state)
        initial = memory_pb2.GameUpdate(
            type=memory_pb2.UPDATE_TYPE_UNSPECIFIED,
            state=snapshot,
            server_time=now_timestamp(),
        )
        return sub_id, q, initial

    def unsubscribe(self, sub_id: str) -> None:
        self._hub.remove(sub_id)

    def _cancel_mismatch_timer(self) -> None:
        if self._mismatch_timer is None:
            return
        try:
            self._mismatch_timer.cancel()
        except Exception:
            pass
        self._mismatch_timer = None

    def _finalize_current_game_in_store(self) -> None:
        if self._store is None:
            return
        players = summarize_players(self._state)
        self._store.finalize_players(
            self._state.game_id,
            [
                PlayerRow(
                    player_id=p.player_id,
                    name=p.name,
                    score=p.score,
                    moves=p.moves,
                    avg_response_ms=p.avg_ms,
                    total_response_ms=p.total_ms,
                )
                for p in players
            ],
        )
        self._store.mark_game_finished(self._state.game_id)

    def _create_fresh_state(self) -> GameState:
        config = self._state.config
        board = Board(config.rows, config.cols, default_emoji_pool())
        return GameState(config=config, board=board)

    def _broadcast(self, update_type: int, message: str) -> None:
        with self._lock:
            self._state.bump_seq(message)
            snapshot = state_to_board_state(self._state)
        update = memory_pb2.GameUpdate(
            type=update_type,
            state=snapshot,
            server_time=now_timestamp(),
        )
        self._hub.publish(update)

    def join(self, player_name: str) -> tuple[str, memory_pb2.BoardState]:
        with self._lock:
            player_id = self._state.join_player(player_name)
            self._state.bump_seq(f"Player joined: {player_name} ({player_id})")
            snapshot = state_to_board_state(self._state)

        if self._store is not None:
            self._store.upsert_player(self._state.game_id, player_id, player_name)

        self._hub.publish(
            memory_pb2.GameUpdate(
                type=memory_pb2.PLAYER_JOINED,
                state=snapshot,
                server_time=now_timestamp(),
            )
        )

        should_start = False
        with self._lock:
            should_start = self._state.can_start() and not self._state.game_started

        if should_start:
            with self._lock:
                self._state.start_game()
            if self._store is not None:
                self._store.mark_game_started(self._state.game_id)
            self._broadcast(memory_pb2.GAME_STARTED, "Game started")

        # Return latest snapshot (in case the game started).
        return player_id, self.get_state()

    def get_state(self) -> memory_pb2.BoardState:
        with self._lock:
            return state_to_board_state(self._state)

    def kick_player(self, player_id: str) -> MoveOutcome:
        with self._lock:
            self._cancel_mismatch_timer()
            try:
                message = self._state.remove_player(player_id)
                self._state.bump_seq(message)
                snapshot = state_to_board_state(self._state)
                game_over_now = self._state.game_over
            except Exception as exc:  # noqa: BLE001
                self._state.bump_seq(str(exc))
                snapshot = state_to_board_state(self._state)
                return MoveOutcome(ok=False, message=str(exc), state=snapshot)

        update_type = memory_pb2.GAME_OVER if game_over_now else memory_pb2.PLAYER_LEFT
        self._hub.publish(
            memory_pb2.GameUpdate(
                type=update_type,
                state=snapshot,
                server_time=now_timestamp(),
            )
        )

        if game_over_now:
            print_final_stats(self._state)
            self._finalize_current_game_in_store()

        return MoveOutcome(ok=True, message=message, state=snapshot)

    def reset_game(self) -> MoveOutcome:
        with self._lock:
            self._cancel_mismatch_timer()
            old_started = self._state.game_started
            old_finished = self._state.game_over

            if self._store is not None and old_started and not old_finished:
                self._finalize_current_game_in_store()

            self._state = self._create_fresh_state()
            self._state.bump_seq("Game reset by admin. Waiting for players...")
            snapshot = state_to_board_state(self._state)

            if self._store is not None:
                cfg = self._state.config
                self._store.create_game(
                    game_id=self._state.game_id,
                    rows=cfg.rows,
                    cols=cfg.cols,
                    max_players=cfg.max_players,
                    mismatch_hide_delay_ms=cfg.mismatch_hide_delay_ms,
                )

        self._hub.publish(
            memory_pb2.GameUpdate(
                type=memory_pb2.GAME_RESET,
                state=snapshot,
                server_time=now_timestamp(),
            )
        )
        return MoveOutcome(ok=True, message="Game reset", state=snapshot)

    def play_move(self, player_id: str, row: int, col: int) -> MoveOutcome:
        pos = Position(row=row, col=col)

        mismatch_to_hide: tuple[Position, Position] | None = None
        turn_result: TurnResult | None = None

        with self._lock:
            try:
                message, turn_result, mismatch_to_hide = self._state.pick(player_id, pos)
                # After every pick we push an update.
                self._state.bump_seq(message)
                snapshot = state_to_board_state(self._state)
            except Exception as exc:  # noqa: BLE001
                self._state.bump_seq(str(exc))
                snapshot = state_to_board_state(self._state)
                return MoveOutcome(ok=False, message=str(exc), state=snapshot)

        if self._store is not None:
            selection_index = 2 if turn_result is not None else 1
            result = "SECOND" if turn_result is not None else "FIRST"
            if turn_result is not None:
                result = "MATCH" if turn_result.match else "MISMATCH"
            self._store.record_move(
                game_id=self._state.game_id,
                player_id=player_id,
                seq=snapshot.seq,
                row=row,
                col=col,
                selection_index=selection_index,
                result=result,
            )

        self._hub.publish(
            memory_pb2.GameUpdate(
                type=memory_pb2.CARD_REVEALED,
                state=snapshot,
                server_time=now_timestamp(),
            )
        )

        if turn_result is None:
            return MoveOutcome(ok=True, message=message, state=snapshot)

        # Turn completed (second pick)
        if mismatch_to_hide is None:
            # Match: advance turn immediately.
            with self._lock:
                if self._state.board.all_matched():
                    self._state.set_game_over()
                    self._state.bump_seq("Game over")
                else:
                    self._state.advance_turn()
                    self._state.bump_seq(
                        f"Turn changed. Now: {self._state.current_turn_player_id()}"
                    )
                snapshot2 = state_to_board_state(self._state)

            if self._store is not None:
                self._store.record_turn(
                    game_id=self._state.game_id,
                    player_id=player_id,
                    turn_no=turn_result.turn_no,
                    response_ms=turn_result.response_ms,
                    matched=True,
                )

            update_type = memory_pb2.GAME_OVER if self._state.game_over else memory_pb2.TURN_CHANGED
            self._hub.publish(
                memory_pb2.GameUpdate(
                    type=update_type,
                    state=snapshot2,
                    server_time=now_timestamp(),
                )
            )

            if self._state.game_over:
                # Always print local stats at the end.
                print_final_stats(self._state)

                if self._store is not None:
                    players = summarize_players(self._state)
                    self._store.finalize_players(
                        self._state.game_id,
                        [
                            PlayerRow(
                                player_id=p.player_id,
                                name=p.name,
                                score=p.score,
                                moves=p.moves,
                                avg_response_ms=p.avg_ms,
                                total_response_ms=p.total_ms,
                            )
                            for p in players
                        ],
                    )
                    self._store.mark_game_finished(self._state.game_id)

            return MoveOutcome(ok=True, message="Match!", state=snapshot2)

        # Mismatch: reveal stays briefly, then hide and change turn.
        with self._lock:
            self._state.phase = Phase.RESOLVING_MISMATCH
            self._state.bump_seq("No match. Cards will be hidden...")
            snapshot3 = state_to_board_state(self._state)

        if self._store is not None:
            self._store.record_turn(
                game_id=self._state.game_id,
                player_id=player_id,
                turn_no=turn_result.turn_no,
                response_ms=turn_result.response_ms,
                matched=False,
            )

        self._hub.publish(
            memory_pb2.GameUpdate(
                type=memory_pb2.TURN_RESOLVED,
                state=snapshot3,
                server_time=now_timestamp(),
            )
        )

        delay_s = self._state.config.mismatch_hide_delay_ms / 1000.0

        def _hide_and_advance() -> None:
            with self._lock:
                if self._state.game_over:
                    return
                pos1, pos2 = mismatch_to_hide
                self._state.board.hide(pos1)
                self._state.board.hide(pos2)
                self._state.phase = Phase.IN_TURN
                self._state.advance_turn()
                self._state.bump_seq(
                    f"Turn changed. Now: {self._state.current_turn_player_id()}"
                )
                snapshot4 = state_to_board_state(self._state)

            self._hub.publish(
                memory_pb2.GameUpdate(
                    type=memory_pb2.TURN_CHANGED,
                    state=snapshot4,
                    server_time=now_timestamp(),
                )
            )

        # Cancel any old timer (defensive)
        self._cancel_mismatch_timer()

        self._mismatch_timer = threading.Timer(delay_s, _hide_and_advance)
        self._mismatch_timer.daemon = True
        self._mismatch_timer.start()

        return MoveOutcome(ok=True, message="No match", state=snapshot3)

