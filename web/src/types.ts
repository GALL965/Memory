export type CellState = "CELL_STATE_UNSPECIFIED" | "HIDDEN" | "REVEALED" | "MATCHED";

export interface CellView {
  row: number;
  col: number;
  state: CellState;
  emoji: string;
}

export interface BoardView {
  rows: number;
  cols: number;
  cells: CellView[];
}

export interface PlayerInfo {
  player_id: string;
  name: string;
  score: number;
  moves: number;
  avg_response_ms: number;
}

export interface BoardState {
  game_id: string;
  lobby_open: boolean;
  game_started: boolean;
  game_over: boolean;
  current_turn_player_id: string;
  players: PlayerInfo[];
  board: BoardView;
  message: string;
  seq: string | number;
}

export interface GameUpdate {
  type: string;
  state: BoardState;
}

export interface JoinResponse {
  player_id: string;
  state: BoardState;
}

export interface PlayMoveResponse {
  ok: boolean;
  message: string;
  state: BoardState;
}

export interface AdminActionResponse {
  ok: boolean;
  message: string;
  state: BoardState;
}

export interface GameSummary {
  game_id: string;
  started_at?: string;
  ended_at?: string;
  rows: number;
  cols: number;
  max_players: number;
  finished: boolean;
}

export interface ListGamesResponse {
  games: GameSummary[];
}

export interface PlayerStats {
  player_id: string;
  name: string;
  score: number;
  moves: number;
  avg_response_ms: number;
  total_response_ms: number;
}

export interface GetGameStatsResponse {
  summary: GameSummary;
  players: PlayerStats[];
}
