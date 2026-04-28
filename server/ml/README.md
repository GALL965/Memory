# Modulo ML: prediccion de acierto por turno

Este directorio contiene los scripts locales de Machine Learning usados por el
proyecto. El objetivo es predecir si un turno completo del juego de memoria
terminara en acierto o fallo.

Para la documentacion academica completa, consultar:

```text
docs/ia_module.md
```

## Dataset

El modelo usa:

```text
dataset_turn_match_prediction.csv
```

Cada fila representa un turno completo de un jugador. La variable objetivo es
`matched`:

- `true` o `1`: el turno encontro pareja.
- `false` o `0`: el turno no encontro pareja.

Columnas como `game_id` y `player_id` se ignoran durante el entrenamiento para
evitar sesgos de identidad.

## Entrenamiento

Desde la raiz del proyecto:

```bash
python server/ml/train_turn_match_model.py --csv dataset_turn_match_prediction.csv
```

El entrenamiento usa `RandomForestClassifier` de `scikit-learn`.

Archivos generados:

```text
server/ml/models/turn_match_model.pkl
server/ml/models/turn_match_model_metadata.json
```

## Prediccion local

Una vez entrenado el modelo, se puede probar una prediccion manual:

```bash
python server/ml/predict_turn_match.py --turn-no 5 --rows 4 --cols 4 --max-players 2 --first-row 1 --first-col 1 --second-row 1 --second-col 3 --response-ms 1500 --matched-pairs-before 2 --matched-pairs-after 2 --cards-remaining-before 12 --board-progress-pct-before 25.0 --player-score-before 1 --player-moves-before 4
```

El resultado muestra:

- prediccion numerica (`1` acierto, `0` fallo)
- interpretacion textual
- probabilidad de acierto
- probabilidad de fallo

## Validacion realizada

El flujo se valido con:

- 1 partida nueva.
- 12 turnos registrados.
- 0 filas con columnas nuevas nulas.
- CSV generado correctamente.
- modelo entrenado correctamente.
- prediccion local exitosa.

## Limitaciones

El dataset inicial es muy pequeno. Si el entrenamiento muestra accuracy `1.0`,
eso no debe interpretarse como rendimiento real. El modelo actual es
demostrativo y sirve para documentar el flujo completo de IA del proyecto.

Para mejorar la calidad se necesitan mas partidas, distintos jugadores,
distintos tamanos de tablero y comparacion con otros modelos.
