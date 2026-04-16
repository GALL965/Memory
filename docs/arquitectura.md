# Arquitectura

## Componentes

- **Servidor gRPC**: mantiene estado global, turnos, validación y streaming.
- **Clientes**: consola y GUI, reciben updates por stream y envían jugadas.
- **PostgreSQL** (opcional pero recomendado): almacena partidas, movimientos y métricas.

## Flujo principal

1. Jugadores llaman `JoinGame` (lobby).
2. Al llegar N jugadores (`MEMORY_PLAYERS`) el servidor inicia el juego.
3. Clientes se suscriben a `SubscribeToUpdates` y actualizan UI en tiempo real.
4. En su turno, el jugador envía dos veces `PlayMove`.
5. El servidor valida, revela, resuelve pareja/no-pareja y rota el turno.
6. Al finalizar, el servidor notifica `GAME_OVER` y registra estadísticas.
