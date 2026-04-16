# Memory Match (Juego de Memoria) — gRPC distribuido

Servidor central coordina el estado del juego y publica actualizaciones en tiempo real vía **gRPC streaming** (`SubscribeToUpdates`) sin polling.

## Requisitos

- Python 3.12+
- (Opcional) Docker + docker compose para LAN

## Setup local (venv)

```bash
cd /path/al/workspace/memory
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./scripts/gen_proto.sh
```

## Ejecutar servidor (local)

```bash
. .venv/bin/activate
export MEMORY_PLAYERS=3
export MEMORY_ROWS=4
export MEMORY_COLS=4
python server/main.py
```

## Ejecutar cliente consola

```bash
. .venv/bin/activate
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Alice
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Bob
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Carol
```

## Ejecutar cliente GUI (Tkinter)

```bash
. .venv/bin/activate
python clients/gui/main.py --host 127.0.0.1 --port 50051 --name Alice
```

## Docker (PostgreSQL + Server)

Desde la carpeta `deploy/`:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Para levantar clientes en contenedor (opcional):

```bash
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Alice
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Bob
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Carol
```

## Persistencia (consultar partidas)

El servidor guarda partidas/movimientos/turnos en PostgreSQL cuando `MEMORY_DB_DSN` está configurado.

RPCs disponibles:

- `ListGames(limit)`
- `GetGameStats(game_id)`

Cliente admin (consola) para consultar:

```bash
. .venv/bin/activate
python clients/admin/main.py --host 127.0.0.1 --port 50051 list --limit 10
python clients/admin/main.py --host 127.0.0.1 --port 50051 stats <game_id>
```

Nota: si corres el servidor sin `MEMORY_DB_DSN`, estos RPCs responderán error de precondición.

## Notas de reglas

- Tamaño de tablero: mínimo 4x4, máximo 8x8.
- Un turno se compone de **dos selecciones**.
- Si no hay pareja, el servidor deja reveladas las 2 cartas por `MEMORY_MISMATCH_DELAY_MS` y luego las oculta.
- Puntaje: +1 por pareja encontrada.
