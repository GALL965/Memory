import { useEffect, useState } from "react";
import { fetchState, getGameStats, kickPlayer, listGames, resetGame } from "../api";
import { BoardGrid } from "../components/BoardGrid";
import type { BoardState, GetGameStatsResponse, GameSummary } from "../types";
import { useBoardStream } from "../useBoardStream";

export function ServerScreen() {
  const [state, setState] = useState<BoardState | null>(null);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [stats, setStats] = useState<GetGameStatsResponse | null>(null);
  const [selectedGame, setSelectedGame] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loadingGames, setLoadingGames] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [adminBusy, setAdminBusy] = useState<string | null>(null);

  const { latestUpdate, connected, error: streamError } = useBoardStream("spectator");

  useEffect(() => {
    if (latestUpdate?.state) {
      setState(latestUpdate.state);
    }
  }, [latestUpdate]);

  useEffect(() => {
    fetchState()
      .then((snapshot) => setState(snapshot))
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "No se pudo cargar estado");
      });
  }, []);

  const refreshGames = async () => {
    setLoadingGames(true);
    setError(null);
    try {
      const response = await listGames(10);
      setGames(response.games || []);
      if (!selectedGame && response.games?.length) {
        setSelectedGame(response.games[0].game_id);
      }
    } catch (listError) {
      setError(listError instanceof Error ? listError.message : "No se pudo listar partidas");
    } finally {
      setLoadingGames(false);
    }
  };

  useEffect(() => {
    refreshGames().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selectedGame) {
      setStats(null);
      return;
    }
    setLoadingStats(true);
    getGameStats(selectedGame)
      .then((response) => setStats(response))
      .catch((statsError) => {
        setStats(null);
        setError(statsError instanceof Error ? statsError.message : "No se pudo cargar stats");
      })
      .finally(() => setLoadingStats(false));
  }, [selectedGame]);

  const handleKick = async (playerId: string) => {
    setAdminBusy(playerId);
    setError(null);
    try {
      const response = await kickPlayer(playerId);
      setState(response.state);
      if (!response.ok) {
        setError(response.message || "No se pudo expulsar al jugador");
      }
    } catch (kickError) {
      setError(kickError instanceof Error ? kickError.message : "No se pudo expulsar al jugador");
    } finally {
      setAdminBusy(null);
    }
  };

  const handleReset = async () => {
    setAdminBusy("reset");
    setError(null);
    try {
      const response = await resetGame();
      setState(response.state);
      if (!response.ok) {
        setError(response.message || "No se pudo reiniciar la partida");
      }
      await refreshGames();
      setSelectedGame("");
      setStats(null);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "No se pudo reiniciar la partida");
    } finally {
      setAdminBusy(null);
    }
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Pantalla Servidor</h2>
        <p>Vista de control para monitorear estado global, tablero y estadísticas históricas.</p>
      </div>

      <div className="badge-row">
        <span className={`badge ${connected ? "ok" : "warn"}`}>
          {connected ? "Stream activo" : "Reconectando stream"}
        </span>
        <span className="badge">Partida: {state?.game_id?.slice(0, 8) || "N/A"}</span>
        <span className="badge">Turno: {state?.current_turn_player_id?.slice(0, 8) || "N/A"}</span>
        <button
          type="button"
          onClick={handleReset}
          disabled={adminBusy !== null}
          className="danger-btn"
        >
          {adminBusy === "reset" ? "Reiniciando..." : "Reiniciar partida"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {streamError && <p className="warn-text">{streamError}</p>}

      <BoardGrid state={state} />

      <div className="scoreboard">
        <h3>Scoreboard en vivo</h3>
        <div className="score-list">
          {(state?.players ?? []).map((player) => (
            <article key={player.player_id} className="score-item">
              <strong>{player.name}</strong>
              <span>score {player.score}</span>
              <span>moves {player.moves}</span>
              <span>avg {player.avg_response_ms.toFixed(1)} ms</span>
              <button
                type="button"
                className="warn-btn"
                onClick={() => handleKick(player.player_id)}
                disabled={adminBusy !== null}
              >
                {adminBusy === player.player_id ? "Expulsando..." : "Expulsar"}
              </button>
            </article>
          ))}
        </div>
      </div>

      <div className="history-block">
        <div className="history-head">
          <h3>Historial de partidas (DB)</h3>
          <button type="button" onClick={refreshGames} disabled={loadingGames}>
            {loadingGames ? "Cargando..." : "Refrescar"}
          </button>
        </div>

        <div className="history-layout">
          <div className="history-list">
            {games.map((game) => (
              <button
                key={game.game_id}
                type="button"
                className={`history-item ${selectedGame === game.game_id ? "active" : ""}`}
                onClick={() => setSelectedGame(game.game_id)}
              >
                <span>{game.game_id.slice(0, 8)}</span>
                <small>
                  {game.rows}x{game.cols} | players {game.max_players} |{" "}
                  {game.finished ? "finished" : "running"}
                </small>
              </button>
            ))}
            {games.length === 0 && <p className="muted">No hay partidas registradas todavía.</p>}
          </div>

          <div className="history-detail">
            <h4>Detalle de partida</h4>
            {loadingStats && <p className="muted">Cargando estadísticas...</p>}
            {!loadingStats && stats && (
              <>
                <p className="muted">
                  game_id: {stats.summary?.game_id?.slice(0, 12)} | finished:{" "}
                  {String(stats.summary?.finished)}
                </p>
                <div className="stats-list">
                  {stats.players?.map((player) => (
                    <article key={player.player_id} className="score-item">
                      <strong>{player.name}</strong>
                      <span>score {player.score}</span>
                      <span>moves {player.moves}</span>
                      <span>avg {player.avg_response_ms.toFixed(1)} ms</span>
                      <span>total {player.total_response_ms.toFixed(1)} ms</span>
                    </article>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
