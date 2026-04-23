import { useEffect, useMemo, useState } from "react";
import type { GameUpdate } from "./types";

export function useBoardStream(playerId: string | null) {
  const [latestUpdate, setLatestUpdate] = useState<GameUpdate | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsUrl = useMemo(() => {
    if (!playerId) {
      return null;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}/ws/updates?player_id=${encodeURIComponent(playerId)}`;
  }, [playerId]);

  useEffect(() => {
    if (!wsUrl) {
      setConnected(false);
      setError(null);
      setLatestUpdate(null);
      return;
    }

    let stopped = false;
    let socket: WebSocket | null = null;
    let retryHandle: number | null = null;

    const connect = () => {
      socket = new WebSocket(wsUrl);
      socket.onopen = () => {
        setConnected(true);
        setError(null);
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as GameUpdate;
          setLatestUpdate(payload);
        } catch {
          setError("No se pudo parsear un update del servidor");
        }
      };
      socket.onerror = () => {
        setError("Error en el stream WebSocket");
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) {
          retryHandle = window.setTimeout(connect, 1200);
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryHandle !== null) {
        window.clearTimeout(retryHandle);
      }
      socket?.close();
    };
  }, [wsUrl]);

  return { latestUpdate, connected, error };
}
