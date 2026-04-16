from __future__ import annotations

from google.protobuf import timestamp_pb2

from server.domain.board import CellState
from server.domain.game_state import GameState
from shared.grpc import memory_pb2


def _cell_state_to_proto(state: CellState) -> int:
    if state == CellState.HIDDEN:
        return memory_pb2.HIDDEN
    if state == CellState.REVEALED:
        return memory_pb2.REVEALED
    if state == CellState.MATCHED:
        return memory_pb2.MATCHED
    return memory_pb2.CELL_STATE_UNSPECIFIED


def state_to_board_state(gs: GameState) -> memory_pb2.BoardState:
    board_cells = []
    for cell in gs.board.get_public_view():
        board_cells.append(
            memory_pb2.CellView(
                row=cell.pos.row,
                col=cell.pos.col,
                state=_cell_state_to_proto(cell.state),
                emoji=cell.emoji,
            )
        )

    board = memory_pb2.BoardView(rows=gs.board.rows, cols=gs.board.cols, cells=board_cells)

    players = []
    for player_id in gs.turn_order:
        player = gs.players[player_id]
        players.append(
            memory_pb2.PlayerInfo(
                player_id=player.player_id,
                name=player.name,
                score=player.score,
                moves=player.moves,
                avg_response_ms=player.avg_response_ms(),
            )
        )

    return memory_pb2.BoardState(
        game_id=gs.game_id,
        config=memory_pb2.GameConfig(
            rows=gs.config.rows,
            cols=gs.config.cols,
            max_players=gs.config.max_players,
            mismatch_hide_delay_ms=gs.config.mismatch_hide_delay_ms,
        ),
        lobby_open=gs.lobby_open,
        game_started=gs.game_started,
        game_over=gs.game_over,
        current_turn_player_id=gs.current_turn_player_id(),
        players=players,
        board=board,
        message=gs.message,
        seq=gs.seq,
    )


def now_timestamp() -> timestamp_pb2.Timestamp:
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    return ts
