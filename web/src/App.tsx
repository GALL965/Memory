import { useState } from "react";
import { ClientScreen } from "./screens/ClientScreen";
import { ServerScreen } from "./screens/ServerScreen";

type Mode = "server" | "client";

export function App() {
  const [mode, setMode] = useState<Mode>("server");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Memory gRPC</p>
          <h1>Control & Play Console</h1>
        </div>
        <div className="switcher">
          <button
            type="button"
            className={mode === "server" ? "active" : ""}
            onClick={() => setMode("server")}
          >
            Servidor
          </button>
          <button
            type="button"
            className={mode === "client" ? "active" : ""}
            onClick={() => setMode("client")}
          >
            Clientes
          </button>
        </div>
      </header>

      <main>{mode === "server" ? <ServerScreen /> : <ClientScreen />}</main>
    </div>
  );
}
