# Memory Match: juego de memoria distribuido con gRPC

Memory Match es un juego de memoria multijugador construido como un sistema
distribuido. Un servidor central mantiene el estado del tablero, controla los
turnos, valida jugadas y publica actualizaciones en tiempo real mediante
**gRPC streaming**.

El proyecto tambien incluye clientes de consola, cliente GUI con Tkinter,
gateway HTTP/WebSocket para web, frontend React, persistencia en PostgreSQL y
un modulo de Machine Learning para generar un dataset y entrenar un modelo
demostrativo.

## Objetivo del proyecto

El objetivo principal es demostrar una arquitectura cliente-servidor en red
usando gRPC. El servidor es la fuente de verdad del juego y los clientes solo
envian acciones o reciben actualizaciones.

El proyecto cubre:

- comunicacion distribuida con gRPC;
- actualizaciones en tiempo real sin polling;
- clientes multiples jugando una misma partida;
- persistencia de partidas, turnos y metricas;
- interfaz web con gateway HTTP/WebSocket;
- generacion de dataset para Machine Learning;
- entrenamiento y prediccion local de un modelo de IA.

## Arquitectura general

```text
Clientes consola / GUI
        |
        | gRPC
        v
Servidor gRPC
        |
        | guarda partidas, jugadores, movimientos y turnos
        v
PostgreSQL

Frontend React
        |
        | HTTP + WebSocket
        v
Gateway FastAPI
        |
        | gRPC
        v
Servidor gRPC
```

## Componentes principales

| Carpeta / archivo | Descripcion |
|---|---|
| `proto/memory.proto` | Contrato gRPC: servicios, mensajes, estados y eventos. |
| `server/` | Servidor central, reglas del juego, streaming y persistencia. |
| `server/domain/` | Logica pura del tablero, jugadores, turnos y reglas. |
| `server/storage/` | Esquema PostgreSQL, acceso a datos y exportacion CSV. |
| `shared/` | Codigo compartido y archivos generados de protobuf. |
| `clients/console/` | Cliente de consola para jugar por terminal. |
| `clients/gui/` | Cliente grafico con Tkinter. |
| `clients/admin/` | Cliente administrativo para consultar partidas y estadisticas. |
| `gateway/` | API FastAPI que traduce HTTP/WebSocket hacia gRPC. |
| `web/` | Frontend React/Vite para servidor y jugadores. |
| `server/ml/` | Entrenamiento y prediccion local del modulo de IA. |
| `deploy/` | Dockerfiles y `docker-compose.yml`. |
| `docs/` | Documentacion de arquitectura, dataset e IA. |

## Flujo del juego

1. Los jugadores se unen llamando a `JoinGame`.
2. El servidor asigna un `player_id` unico.
3. Cuando se alcanza el numero configurado de jugadores, inicia la partida.
4. Los clientes se suscriben a `SubscribeToUpdates`.
5. En cada turno, el jugador selecciona dos cartas con `PlayMove`.
6. El servidor valida si es su turno y si las cartas son validas.
7. Si las cartas coinciden, se marca pareja y se suma un punto.
8. Si no coinciden, se muestran temporalmente y luego se ocultan.
9. El servidor cambia el turno y publica el nuevo estado.
10. Al terminar la partida, se guardan metricas y estadisticas.

## Reglas principales

- El tablero puede ser `4x4`, `6x6` u `8x8`.
- Un turno completo tiene dos selecciones.
- Cada pareja encontrada suma `+1` punto.
- Si no hay pareja, las cartas se ocultan despues de
  `MEMORY_MISMATCH_DELAY_MS`.
- El servidor controla todas las reglas; los clientes no modifican el estado
  directamente.

## Requisitos

- Python 3.12 recomendado.
- Docker y Docker Compose para levantar todo el sistema.
- Node.js 20 si se quiere ejecutar el frontend fuera de Docker.

Dependencias Python principales:

- `grpcio`
- `grpcio-tools`
- `protobuf`
- `psycopg`
- `fastapi`
- `pandas`
- `scikit-learn`
- `joblib`

## Configuracion

El archivo `.env.example` muestra las variables disponibles:

```env
MEMORY_HOST=0.0.0.0
MEMORY_PORT=50051
MEMORY_ROWS=8
MEMORY_COLS=8
MEMORY_PLAYERS=3
MEMORY_MISMATCH_DELAY_MS=1000
MEMORY_DB_DSN=postgresql://postgres:postgres@localhost:5432/memory
```

Variables importantes:

| Variable | Uso |
|---|---|
| `MEMORY_HOST` | Host donde escucha el servidor gRPC. |
| `MEMORY_PORT` | Puerto del servidor gRPC. |
| `MEMORY_ROWS` / `MEMORY_COLS` | Tamano inicial del tablero. |
| `MEMORY_PLAYERS` | Jugadores necesarios para iniciar. |
| `MEMORY_MISMATCH_DELAY_MS` | Tiempo para ocultar cartas fallidas. |
| `MEMORY_DB_DSN` | Conexion PostgreSQL para persistencia. |

## Ejecucion con Docker

Desde la raiz del proyecto:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Esto levanta:

- `db`: PostgreSQL.
- `server`: servidor gRPC.
- `gateway`: API HTTP/WebSocket hacia gRPC.
- `web`: frontend React servido con Nginx.

URLs y puertos:

| Servicio | URL / puerto |
|---|---|
| Frontend web | `http://localhost:5173` |
| Gateway FastAPI | `http://localhost:8000` |
| Servidor gRPC | `localhost:50051` |
| PostgreSQL | `localhost:5432` |

Clientes en contenedor:

```bash
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Alice
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Bob
docker compose -f deploy/docker-compose.yml --profile clients run --rm client_console --name Carol
```

## Ejecucion local sin Docker

Crear entorno e instalar dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Regenerar protobuf si se modifica `proto/memory.proto`:

```bash
bash scripts/gen_proto.sh
```

Levantar servidor:

```bash
set MEMORY_PLAYERS=3
set MEMORY_ROWS=8
set MEMORY_COLS=8
python server/main.py
```

En Linux/macOS:

```bash
export MEMORY_PLAYERS=3
export MEMORY_ROWS=8
export MEMORY_COLS=8
python server/main.py
```

## Clientes

Cliente de consola:

```bash
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Alice
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Bob
python clients/console/main.py --host 127.0.0.1 --port 50051 --name Carol
```

Cliente GUI con Tkinter:

```bash
python clients/gui/main.py --host 127.0.0.1 --port 50051 --name Alice
```

Cliente administrativo:

```bash
python clients/admin/main.py --host 127.0.0.1 --port 50051 list --limit 10
python clients/admin/main.py --host 127.0.0.1 --port 50051 stats <game_id>
```

## Frontend web

La web tiene dos pantallas:

- `Servidor`: monitoreo del tablero, jugadores, historial, estadisticas,
  reinicio de partida y expulsion de jugadores.
- `Clientes`: union de jugadores y juego en tiempo real.

Con Docker:

```text
http://localhost:5173
```

En desarrollo local:

```bash
cd web
npm install
npm run dev
```

Por defecto Vite usa proxy hacia `http://localhost:8000`.

## Persistencia en PostgreSQL

Cuando `MEMORY_DB_DSN` esta configurado, el servidor guarda:

- partidas en `games`;
- jugadores en `game_players`;
- movimientos individuales en `moves`;
- turnos completos en `turns`.

La persistencia permite consultar historial, estadisticas finales y construir
datasets para analisis o IA.

## Modulo de IA

El proyecto incluye un flujo completo de IA demostrativo. El objetivo es
predecir si un turno completo sera correcto o incorrecto.

Variable objetivo:

```text
matched
```

Interpretacion:

- `true` / `1`: el turno encontro pareja.
- `false` / `0`: el turno no encontro pareja.

Flujo:

```text
Juego gRPC
-> GameManager captura contexto del turno
-> PostgreSQL guarda los datos
-> export_turn_dataset.py genera CSV
-> train_turn_match_model.py entrena modelo
-> predict_turn_match.py realiza prediccion local
```

Exportar dataset:

```bash
python server/storage/export_turn_dataset.py --output dataset_turn_match_prediction.csv
```

Entrenar modelo:

```bash
python server/ml/train_turn_match_model.py --csv dataset_turn_match_prediction.csv
```

Probar prediccion local:

```bash
python server/ml/predict_turn_match.py --turn-no 5 --rows 4 --cols 4 --max-players 2 --first-row 1 --first-col 1 --second-row 1 --second-col 3 --response-ms 1500 --matched-pairs-before 2 --matched-pairs-after 2 --cards-remaining-before 12 --board-progress-pct-before 25.0 --player-score-before 1 --player-moves-before 4
```

Archivos generados:

- `dataset_turn_match_prediction.csv`
- `server/ml/models/turn_match_model.pkl`
- `server/ml/models/turn_match_model_metadata.json`

Documentacion relacionada:

- `docs/ia_dataset.md`
- `docs/ia_module.md`
- `server/ml/README.md`

## Dataset de IA

El dataset principal es:

```text
dataset_turn_match_prediction.csv
```

Cada fila representa un turno completo. Algunas columnas importantes:

- `turn_no`
- `rows`
- `cols`
- `max_players`
- `first_row`
- `first_col`
- `second_row`
- `second_col`
- `response_ms`
- `matched_pairs_before`
- `matched_pairs_after`
- `cards_remaining_before`
- `board_progress_pct_before`
- `player_score_before`
- `player_moves_before`
- `matched`

El modelo actual usa `RandomForestClassifier` de `scikit-learn`.

## Limitaciones actuales

- El modelo de IA es demostrativo.
- Un dataset pequeno puede producir metricas artificialmente altas.
- Se necesitan mas partidas para entrenar un modelo confiable.
- `game_id` y `player_id` se conservan para trazabilidad, pero no se usan como
  features para evitar sesgos de identidad.
- La prediccion todavia es local; no se integra al gateway ni al frontend.

## Trabajo futuro

- Recolectar mas partidas reales.
- Automatizar partidas para generar mas datos.
- Comparar modelos como Logistic Regression, Decision Tree y Random Forest.
- Agregar validacion cruzada.
- Crear endpoint de prediccion en FastAPI.
- Mostrar probabilidad de acierto en el frontend.
- Exportar reportes o graficas del desempeno del modelo.

## Documentacion adicional

- `docs/arquitectura.md`: arquitectura del sistema.
- `docs/checklist.md`: checklist de validacion del proyecto.
- `docs/ia_dataset.md`: descripcion del dataset.
- `docs/ia_module.md`: documentacion formal del modulo de IA.
- `server/ml/README.md`: guia practica del modulo ML.
