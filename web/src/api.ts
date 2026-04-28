import type {
  AdminActionResponse,
  BoardState,
  GetGameStatsResponse,
  JoinResponse,
  ListGamesResponse,
  PlayMoveResponse
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const json = (await response.json()) as { detail?: string };
      if (json.detail) {
        detail = json.detail;
      }
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function joinGame(name: string): Promise<JoinResponse> {
  return request<JoinResponse>("/api/join", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export function playMove(playerId: string, row: number, col: number): Promise<PlayMoveResponse> {
  return request<PlayMoveResponse>("/api/move", {
    method: "POST",
    body: JSON.stringify({
      player_id: playerId,
      row,
      col
    })
  });
}

export function kickPlayer(playerId: string): Promise<AdminActionResponse> {
  return request<AdminActionResponse>("/api/admin/kick", {
    method: "POST",
    body: JSON.stringify({ player_id: playerId })
  });
}

export function resetGame(rows?: number, cols?: number): Promise<AdminActionResponse> {
  return request<AdminActionResponse>("/api/admin/reset", {
    method: "POST",
    body: JSON.stringify({
      rows,
      cols
    })
  });
}

export function fetchState(playerId = ""): Promise<BoardState> {
  const params = new URLSearchParams();
  if (playerId) {
    params.set("player_id", playerId);
  }
  const query = params.toString();
  return request<BoardState>(`/api/state${query ? `?${query}` : ""}`);
}

export function listGames(limit = 10): Promise<ListGamesResponse> {
  return request<ListGamesResponse>(`/api/games?limit=${limit}`);
}

export function getGameStats(gameId: string): Promise<GetGameStatsResponse> {
  return request<GetGameStatsResponse>(`/api/games/${encodeURIComponent(gameId)}/stats`);
}
