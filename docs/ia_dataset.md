# Dataset IA: prediccion de acierto por turno

Este documento describe el dataset usado por el modulo de inteligencia
artificial del juego de memoria distribuido.

## Objetivo

El dataset permite entrenar un modelo para predecir si un turno completo del
juego sera correcto o incorrecto.

La variable objetivo es:

- `matched`: `true` si las dos cartas seleccionadas forman pareja, `false` si no.

## Unidad de analisis

Cada fila representa un turno completo de un jugador. Un turno completo incluye
dos selecciones de cartas.

## Archivo generado

```text
dataset_turn_match_prediction.csv
```

El archivo se genera desde PostgreSQL con:

```bash
python server/storage/export_turn_dataset.py --output dataset_turn_match_prediction.csv
```

La exportacion usa la variable de entorno `MEMORY_DB_DSN`.

## Columnas

| Columna | Tipo aproximado | Descripcion | Uso |
|---|---:|---|---|
| `game_id` | texto UUID | Identificador de la partida. | contexto |
| `turn_no` | entero | Numero de turno dentro de la partida. | feature |
| `player_id` | texto UUID | Identificador del jugador. | contexto |
| `rows` | entero | Filas del tablero. | feature |
| `cols` | entero | Columnas del tablero. | feature |
| `max_players` | entero | Numero maximo de jugadores. | feature |
| `first_row` | entero | Fila de la primera carta seleccionada. | feature |
| `first_col` | entero | Columna de la primera carta seleccionada. | feature |
| `second_row` | entero | Fila de la segunda carta seleccionada. | feature |
| `second_col` | entero | Columna de la segunda carta seleccionada. | feature |
| `response_ms` | decimal | Tiempo del turno en milisegundos. | feature |
| `matched_pairs_before` | entero | Parejas encontradas antes del turno. | feature |
| `matched_pairs_after` | entero | Parejas encontradas despues del turno. | feature |
| `cards_remaining_before` | entero | Cartas sin emparejar antes del turno. | feature |
| `board_progress_pct_before` | decimal | Porcentaje del tablero resuelto antes del turno. | feature |
| `player_score_before` | entero | Puntaje del jugador antes del turno. | feature |
| `player_moves_before` | entero | Selecciones acumuladas del jugador antes del turno. | feature |
| `matched` | booleano | Resultado del turno: acierto o fallo. | label |

`game_id` y `player_id` se conservan para trazabilidad, pero no se usan como
features del modelo actual.

## Limitaciones

- El dataset inicial es pequeno.
- Las metricas del modelo no son confiables con pocas filas.
- Si existen partidas antiguas, algunas columnas nuevas pueden aparecer como
  `NULL`.
- No se guardan como features publicas todas las cartas ocultas del tablero.
- Se necesitan muchas partidas reales para entrenar un modelo mas estable.

Para la descripcion completa del modulo de IA, ver `docs/ia_module.md`.
