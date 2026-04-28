from __future__ import annotations

import asyncio
import os
import queue
import sys
import threading
from typing import Any

import grpc
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel, Field

# Allow running as: python gateway/main.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.client_core import ServerAddress, create_stub
from shared.grpc import memory_pb2


def _as_dict(message: Any) -> dict[str, Any]:
    return MessageToDict(
        message,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
    )


def _http_error_from_rpc(exc: grpc.RpcError) -> HTTPException:
    code = exc.code()
    details = exc.details() or "RPC call failed"
    if code == grpc.StatusCode.NOT_FOUND:
        return HTTPException(status_code=404, detail=details)
    if code in (grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.FAILED_PRECONDITION):
        return HTTPException(status_code=400, detail=details)
    return HTTPException(status_code=502, detail=f"{code.name}: {details}")


class JoinPayload(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class MovePayload(BaseModel):
    player_id: str = Field(min_length=1)
    row: int
    col: int


class KickPayload(BaseModel):
    player_id: str = Field(min_length=1)


class ResetPayload(BaseModel):
    rows: int | None = Field(default=None, ge=4, le=8)
    cols: int | None = Field(default=None, ge=4, le=8)


grpc_host = os.getenv("MEMORY_GRPC_HOST", "server")
grpc_port = int(os.getenv("MEMORY_GRPC_PORT", "50051"))
grpc_address = ServerAddress(grpc_host, grpc_port)
grpc_channel, grpc_stub = create_stub(grpc_address)

app = FastAPI(title="Memory Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/join")
def join(payload: JoinPayload) -> dict[str, Any]:
    try:
        response = grpc_stub.JoinGame(memory_pb2.JoinGameRequest(player_name=payload.name.strip()))
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.post("/api/move")
def play_move(payload: MovePayload) -> dict[str, Any]:
    try:
        response = grpc_stub.PlayMove(
            memory_pb2.PlayMoveRequest(
                player_id=payload.player_id,
                row=payload.row,
                col=payload.col,
            )
        )
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.post("/api/admin/kick")
def kick_player(payload: KickPayload) -> dict[str, Any]:
    try:
        response = grpc_stub.KickPlayer(
            memory_pb2.KickPlayerRequest(
                player_id=payload.player_id,
            )
        )
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.post("/api/admin/reset")
def reset_game(payload: ResetPayload) -> dict[str, Any]:
    try:
        response = grpc_stub.ResetGame(
            memory_pb2.ResetGameRequest(
                rows=payload.rows or 0,
                cols=payload.cols or 0,
            )
        )
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.get("/api/state")
def get_state(player_id: str = Query(default="")) -> dict[str, Any]:
    try:
        response = grpc_stub.GetBoardState(memory_pb2.GetBoardStateRequest(player_id=player_id))
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.get("/api/games")
def list_games(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    try:
        response = grpc_stub.ListGames(memory_pb2.ListGamesRequest(limit=limit))
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.get("/api/games/{game_id}/stats")
def get_game_stats(game_id: str) -> dict[str, Any]:
    try:
        response = grpc_stub.GetGameStats(memory_pb2.GetGameStatsRequest(game_id=game_id))
        return _as_dict(response)
    except grpc.RpcError as exc:
        raise _http_error_from_rpc(exc) from exc


@app.websocket("/ws/updates")
async def updates_stream(websocket: WebSocket, player_id: str = "") -> None:
    await websocket.accept()

    items: queue.Queue[dict[str, Any] | None] = queue.Queue()
    stop_event = threading.Event()
    call_ref: dict[str, Any] = {}

    def _pump() -> None:
        try:
            call = grpc_stub.SubscribeToUpdates(memory_pb2.SubscribeRequest(player_id=player_id))
            call_ref["call"] = call
            for update in call:
                if stop_event.is_set():
                    break
                items.put(_as_dict(update))
        except grpc.RpcError as exc:
            items.put(
                {
                    "type": "ERROR",
                    "state": {"message": f"Subscription ended: {exc.code().name} {exc.details() or ''}"},
                }
            )
        finally:
            items.put(None)

    thread = threading.Thread(target=_pump, daemon=True)
    thread.start()

    try:
        while True:
            item = await asyncio.to_thread(items.get)
            if item is None:
                break
            await websocket.send_json(item)
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        call = call_ref.get("call")
        if call is not None:
            try:
                call.cancel()
            except Exception:
                pass


@app.on_event("shutdown")
def _shutdown() -> None:
    grpc_channel.close()
