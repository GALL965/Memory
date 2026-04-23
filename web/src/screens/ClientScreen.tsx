import { useEffect, useMemo, useState } from "react";
import { joinGame, playMove } from "../api";
import { BoardGrid } from "../components/BoardGrid";
import type { BoardState } from "../types";
import { useBoardStream } from "../useBoardStream";

export function ClientScreen() {
  const [name, setName] = useState("");
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [state, setState] = useState<BoardState | null>(null);
  const [info, setInfo] = useState("Ingresa tu nombre para unirte.");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { latestUpdate, connected, error: streamError } = useBoardStream(playerId);

  useEffect(() => {
    if (latestUpdate?.state) {
      setState(latestUpdate.state);
      setInfo(latestUpdate.state.message || "Update recibido");
    }
  }, [latestUpdate]);

  const myTurn = useMemo(() => {
    if (!playerId || !state) {
      return false;
    }
    return state.game_started && !state.game_over && state.current_turn_player_id === playerId;
  }, [playerId, state]);

  const canPick = (row: number, col: number): boolean => {
    if (!myTurn || busy || !state) {
      return false;
    }
    const cell = state.board.cells.find((item) => item.row === row && item.col === col);
    if (!cell) {
      return false;
    }
    return cell.state === "HIDDEN";
  };

  const handleJoin = async () => {
    const cleanName = name.trim();
    if (!cleanName) {
      setError("Escribe un nombre válido.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await joinGame(cleanName);
      setPlayerId(response.player_id);
      setState(response.state);
      setInfo(`Te uniste como ${cleanName}. Esperando updates...`);
    } catch (joinError) {
      setError(joinError instanceof Error ? joinError.message : "Error al unirse");
    } finally {
      setBusy(false);
    }
  };

  const handlePick = async (row: number, col: number) => {
    if (!playerId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await playMove(playerId, row, col);
      setState(response.state);
      setInfo(response.message);
    } catch (moveError) {
      setError(moveError instanceof Error ? moveError.message : "No se pudo jugar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Pantalla Cliente</h2>
        <p>Esta vista es para cada jugador que participa en la partida.</p>
      </div>

      {!playerId ? (
        <div className="join-form">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nombre del jugador"
            maxLength={40}
          />
          <button type="button" onClick={handleJoin} disabled={busy}>
            {busy ? "Uniendo..." : "Unirme"}
          </button>
        </div>
      ) : (
        <div className="badge-row">
          <span className="badge">ID: {playerId.slice(0, 8)}</span>
          <span className={`badge ${connected ? "ok" : "warn"}`}>
            {connected ? "WS conectado" : "Reconectando stream"}
          </span>
          <span className={`badge ${myTurn ? "turn" : ""}`}>
            {myTurn ? "Es tu turno" : "Esperando turno"}
          </span>
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {streamError && <p className="warn-text">{streamError}</p>}
      <p className="status-line">{info}</p>

      <BoardGrid state={state} onPick={handlePick} canPick={canPick} />

      <div className="scoreboard">
        <h3>Marcador</h3>
        <div className="score-list">
          {(state?.players ?? []).map((player) => (
            <article
              key={player.player_id}
              className={`score-item ${playerId === player.player_id ? "mine" : ""}`}
            >
              <strong>{player.name}</strong>
              <span>score {player.score}</span>
              <span>moves {player.moves}</span>
              <span>avg {player.avg_response_ms.toFixed(1)} ms</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
