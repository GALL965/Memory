# Modulo de inteligencia artificial

## 1. Objetivo del modulo de IA

El modulo de inteligencia artificial del proyecto tiene como objetivo predecir
si un turno del juego de memoria sera correcto o incorrecto.

En este contexto, un turno completo equivale a dos cartas seleccionadas por un
jugador. El resultado del turno se representa con la variable `matched`:

- `true` o `1`: el jugador encontro una pareja.
- `false` o `0`: el jugador no encontro una pareja.

El problema se plantea como una tarea de clasificacion binaria.

## 2. Justificacion

Este enfoque tiene sentido para el proyecto porque el juego genera eventos
naturales por turno. Cada turno tiene un inicio, dos selecciones, un tiempo de
respuesta y un resultado medible.

La variable objetivo es clara: `matched`. Esto permite construir ejemplos
supervisados a partir de datos reales generados por los jugadores, sin inventar
etiquetas externas. Ademas, el servidor ya conoce el estado del tablero, el
jugador activo, el avance de la partida y el resultado de cada turno, por lo
que puede registrar informacion util para analisis y aprendizaje automatico.

## 3. Flujo general

El flujo completo implementado es:

```text
Juego gRPC
-> GameManager captura contexto del turno
-> PostgreSQL guarda los datos
-> export_turn_dataset.py genera CSV
-> train_turn_match_model.py entrena modelo
-> predict_turn_match.py realiza prediccion local
```

Descripcion por etapa:

1. El juego distribuido corre mediante gRPC.
2. `GameManager` procesa cada turno y captura contexto antes y despues de las
   selecciones.
3. PostgreSQL guarda la informacion en las tablas del proyecto, especialmente
   en `turns`.
4. `server/storage/export_turn_dataset.py` exporta los turnos a un CSV.
5. `server/ml/train_turn_match_model.py` entrena un modelo de clasificacion.
6. `server/ml/predict_turn_match.py` carga el modelo y permite predicciones
   locales con datos manuales.

## 4. Dataset

El dataset principal se llama:

```text
dataset_turn_match_prediction.csv
```

La unidad de analisis es un turno completo de un jugador. Cada fila representa
dos cartas seleccionadas y el contexto disponible para ese turno.

La variable objetivo es:

```text
matched
```

El tipo de problema es clasificacion binaria:

- `true`: turno correcto, el jugador encontro pareja.
- `false`: turno incorrecto, el jugador no encontro pareja.

## 5. Columnas del dataset

| Columna | Tipo aproximado | Descripcion | Rol |
|---|---:|---|---|
| `game_id` | texto UUID | Identificador unico de la partida. | contexto |
| `turn_no` | entero | Numero del turno dentro de la partida. | feature |
| `player_id` | texto UUID | Identificador unico del jugador. | contexto |
| `rows` | entero | Numero de filas del tablero. | feature |
| `cols` | entero | Numero de columnas del tablero. | feature |
| `max_players` | entero | Cantidad maxima de jugadores configurada. | feature |
| `first_row` | entero | Fila de la primera carta seleccionada. | feature |
| `first_col` | entero | Columna de la primera carta seleccionada. | feature |
| `second_row` | entero | Fila de la segunda carta seleccionada. | feature |
| `second_col` | entero | Columna de la segunda carta seleccionada. | feature |
| `response_ms` | decimal | Tiempo total del turno en milisegundos. | feature |
| `matched_pairs_before` | entero | Parejas encontradas antes del turno. | feature |
| `matched_pairs_after` | entero | Parejas encontradas despues del turno. | feature |
| `cards_remaining_before` | entero | Cartas no emparejadas antes del turno. | feature |
| `board_progress_pct_before` | decimal | Porcentaje del tablero resuelto antes del turno. | feature |
| `player_score_before` | entero | Puntaje del jugador antes del turno. | feature |
| `player_moves_before` | entero | Selecciones acumuladas del jugador antes del turno. | feature |
| `matched` | booleano | Indica si el turno termino en pareja. | label |

`game_id` y `player_id` se mantienen para trazabilidad, pero el entrenamiento
actual los ignora para evitar introducir sesgos de identidad.

## 6. Modelo usado

El modelo implementado usa:

- Algoritmo: `RandomForestClassifier`.
- Librerias: `pandas`, `scikit-learn`, `joblib`.
- Archivo del modelo: `server/ml/models/turn_match_model.pkl`.
- Archivo de metadata: `server/ml/models/turn_match_model_metadata.json`.

La metadata guarda informacion sobre la fecha de entrenamiento, filas usadas,
features, variable objetivo, accuracy, modelo utilizado y ruta del CSV.

## 7. Comandos de uso

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

## 8. Resultados de validacion

El flujo fue validado con una partida nueva generada desde el servidor del
proyecto:

- Partidas nuevas validadas: `1`.
- Turnos registrados: `12`.
- Filas con columnas nuevas nulas: `0`.
- CSV generado correctamente: si.
- Modelo entrenado: si.
- Prediccion local exitosa: si.

Durante la validacion, el CSV incluyo encabezados, filas reales y valores
`true`/`false` en la columna `matched`.

## 9. Limitaciones

El dataset inicial es pequeno. Por esa razon, una accuracy de `1.0` no representa
rendimiento real del modelo. Con pocas filas, el conjunto de prueba tambien es
pequeno y las metricas pueden ser artificialmente altas o inestables.

Se necesitan mas partidas para entrenar y evaluar correctamente. Tambien es
importante recolectar partidas de distintos jugadores y tableros para evitar
sesgos. Los nombres o identificadores de jugadores no se usan como features
porque pueden inducir al modelo a aprender identidades en lugar de patrones del
juego.

El modelo actual debe entenderse como demostrativo y academico. Su valor
principal es mostrar el flujo completo: captura de datos, persistencia,
exportacion, entrenamiento y prediccion.

## 10. Trabajo futuro

Mejoras posibles:

- Recolectar mas partidas reales.
- Automatizar la generacion de partidas para aumentar el dataset.
- Agregar un endpoint de prediccion en el gateway FastAPI.
- Mostrar en el frontend la probabilidad de acierto antes de jugar un turno.
- Comparar modelos como `LogisticRegression`, `DecisionTreeClassifier` y
  `RandomForestClassifier`.
- Agregar validacion cruzada cuando exista un volumen mayor de datos.
- Analizar balance de clases entre aciertos y fallos.
- Separar datos por tamano de tablero para estudiar dificultad.
