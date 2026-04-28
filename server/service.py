from __future__ import annotations

import queue
from concurrent import futures

import grpc
from google.protobuf import timestamp_pb2

from server.domain.game_state import GameConfig
from server.storage.postgres_store import PostgresStore
from server.game_manager import GameManager
from shared.grpc import memory_pb2, memory_pb2_grpc


class MemoryService(memory_pb2_grpc.MemoryGameServiceServicer):
    def __init__(self, manager: GameManager, store: PostgresStore | None = None):
        self._manager = manager
        self._store = store

    def JoinGame(self, request: memory_pb2.JoinGameRequest, context: grpc.ServicerContext):
        try:
            player_id, state = self._manager.join(request.player_name)
            return memory_pb2.JoinGameResponse(player_id=player_id, state=state)
        except Exception as exc:  # noqa: BLE001
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))

    def PlayMove(self, request: memory_pb2.PlayMoveRequest, context: grpc.ServicerContext):
        outcome = self._manager.play_move(request.player_id, request.row, request.col)
        return memory_pb2.PlayMoveResponse(ok=outcome.ok, message=outcome.message, state=outcome.state)

    def GetBoardState(self, request: memory_pb2.GetBoardStateRequest, context: grpc.ServicerContext):
        # Soft validation: if player_id is unknown, still allow fetching state for debugging.
        state = self._manager.get_state()
        return state

    def SubscribeToUpdates(self, request: memory_pb2.SubscribeRequest, context: grpc.ServicerContext):
        # If player_id is unknown, still allow subscribing (spectator mode).
        sub_id, q, initial = self._manager.subscribe_queue()
        try:
            yield initial
            while context.is_active():
                try:
                    update = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                yield update
        finally:
            self._manager.unsubscribe(sub_id)

    def KickPlayer(self, request: memory_pb2.KickPlayerRequest, context: grpc.ServicerContext):
        outcome = self._manager.kick_player(request.player_id)
        return memory_pb2.KickPlayerResponse(
            ok=outcome.ok,
            message=outcome.message,
            state=outcome.state,
        )

    def ResetGame(self, request: memory_pb2.ResetGameRequest, context: grpc.ServicerContext):
        rows = request.rows if request.rows > 0 else None
        cols = request.cols if request.cols > 0 else None
        outcome = self._manager.reset_game(rows=rows, cols=cols)
        return memory_pb2.ResetGameResponse(
            ok=outcome.ok,
            message=outcome.message,
            state=outcome.state,
        )

    # Persistence-backed RPCs will be implemented after DB layer is added.
    def ListGames(self, request: memory_pb2.ListGamesRequest, context: grpc.ServicerContext):
        if self._store is None:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("DB storage is not configured")
            return memory_pb2.ListGamesResponse()

        games = self._store.list_games(request.limit or 10)
        out = []
        for g in games:
            started = timestamp_pb2.Timestamp()
            ended = timestamp_pb2.Timestamp()
            if g.started_at is not None:
                started.FromDatetime(g.started_at)
            if g.ended_at is not None:
                ended.FromDatetime(g.ended_at)
            out.append(
                memory_pb2.GameSummary(
                    game_id=g.game_id,
                    started_at=started,
                    ended_at=ended,
                    rows=g.rows,
                    cols=g.cols,
                    max_players=g.max_players,
                    finished=g.finished,
                )
            )
        return memory_pb2.ListGamesResponse(games=out)

    def GetGameStats(self, request: memory_pb2.GetGameStatsRequest, context: grpc.ServicerContext):
        if self._store is None:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("DB storage is not configured")
            return memory_pb2.GetGameStatsResponse()

        game = self._store.get_game(request.game_id)
        if game is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Game not found")
            return memory_pb2.GetGameStatsResponse()

        started = timestamp_pb2.Timestamp()
        ended = timestamp_pb2.Timestamp()
        if game.started_at is not None:
            started.FromDatetime(game.started_at)
        if game.ended_at is not None:
            ended.FromDatetime(game.ended_at)

        summary = memory_pb2.GameSummary(
            game_id=game.game_id,
            started_at=started,
            ended_at=ended,
            rows=game.rows,
            cols=game.cols,
            max_players=game.max_players,
            finished=game.finished,
        )

        players = []
        for p in self._store.get_players(request.game_id):
            players.append(
                memory_pb2.PlayerStats(
                    player_id=p.player_id,
                    name=p.name,
                    score=p.score,
                    moves=p.moves,
                    avg_response_ms=p.avg_response_ms,
                    total_response_ms=p.total_response_ms,
                )
            )

        return memory_pb2.GetGameStatsResponse(summary=summary, players=players)


def create_grpc_server(manager: GameManager, store: PostgresStore | None = None) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    memory_pb2_grpc.add_MemoryGameServiceServicer_to_server(MemoryService(manager, store=store), server)
    return server
