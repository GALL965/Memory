from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


FALLBACK_FEATURE_COLUMNS = [
    "turn_no",
    "rows",
    "cols",
    "max_players",
    "first_row",
    "first_col",
    "second_row",
    "second_col",
    "response_ms",
    "matched_pairs_before",
    "matched_pairs_after",
    "cards_remaining_before",
    "board_progress_pct_before",
    "player_score_before",
    "player_moves_before",
]


ARG_TO_FEATURE = {
    "turn_no": "turn_no",
    "rows": "rows",
    "cols": "cols",
    "max_players": "max_players",
    "first_row": "first_row",
    "first_col": "first_col",
    "second_row": "second_row",
    "second_col": "second_col",
    "response_ms": "response_ms",
    "matched_pairs_before": "matched_pairs_before",
    "matched_pairs_after": "matched_pairs_after",
    "cards_remaining_before": "cards_remaining_before",
    "board_progress_pct_before": "board_progress_pct_before",
    "player_score_before": "player_score_before",
    "player_moves_before": "player_moves_before",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict whether a memory-game turn will be a match."
    )
    parser.add_argument("--turn-no", dest="turn_no", type=float, required=True)
    parser.add_argument("--rows", type=float, required=True)
    parser.add_argument("--cols", type=float, required=True)
    parser.add_argument("--max-players", dest="max_players", type=float, required=True)
    parser.add_argument("--first-row", dest="first_row", type=float, required=True)
    parser.add_argument("--first-col", dest="first_col", type=float, required=True)
    parser.add_argument("--second-row", dest="second_row", type=float, required=True)
    parser.add_argument("--second-col", dest="second_col", type=float, required=True)
    parser.add_argument("--response-ms", dest="response_ms", type=float, required=True)
    parser.add_argument(
        "--matched-pairs-before",
        dest="matched_pairs_before",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--matched-pairs-after",
        dest="matched_pairs_after",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--cards-remaining-before",
        dest="cards_remaining_before",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--board-progress-pct-before",
        dest="board_progress_pct_before",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--player-score-before",
        dest="player_score_before",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--player-moves-before",
        dest="player_moves_before",
        type=float,
        required=True,
    )
    return parser.parse_args()


def load_metadata(metadata_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not metadata_path.exists():
        print(
            f"Advertencia: no se encontro metadata en {metadata_path}. "
            "Se usara la lista fija de features."
        )
        return None, FALLBACK_FEATURE_COLUMNS

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    features = metadata.get("feature_columns")
    if not isinstance(features, list) or not all(isinstance(item, str) for item in features):
        print(
            "Advertencia: metadata sin feature_columns valida. "
            "Se usara la lista fija de features."
        )
        return metadata, FALLBACK_FEATURE_COLUMNS

    return metadata, features


def build_input_frame(args: argparse.Namespace, feature_columns: list[str]) -> pd.DataFrame:
    values_by_feature = {
        feature: getattr(args, arg_name)
        for arg_name, feature in ARG_TO_FEATURE.items()
    }
    missing = [feature for feature in feature_columns if feature not in values_by_feature]
    if missing:
        raise ValueError(
            "Faltan argumentos para las features requeridas: " + ", ".join(missing)
        )
    return pd.DataFrame(
        [{feature: values_by_feature[feature] for feature in feature_columns}],
        columns=feature_columns,
    )


def probability_for_class(model: Any, probabilities: Any, class_value: int) -> float | None:
    classes = list(getattr(model, "classes_", []))
    if class_value not in classes:
        return None
    class_index = classes.index(class_value)
    return float(probabilities[0][class_index])


def main() -> int:
    args = parse_args()

    base_dir = Path(__file__).resolve().parent
    model_path = base_dir / "models" / "turn_match_model.pkl"
    metadata_path = base_dir / "models" / "turn_match_model_metadata.json"

    if not model_path.exists():
        print(f"ERROR: no existe el modelo entrenado: {model_path}", file=sys.stderr)
        return 1

    metadata, feature_columns = load_metadata(metadata_path)
    if metadata is not None:
        print(f"Metadata cargada: {metadata_path}")

    try:
        model = joblib.load(model_path)
        input_frame = build_input_frame(args, feature_columns)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Modelo cargado: {model_path}")
    print("Features usadas:")
    for feature in feature_columns:
        print(f"- {feature}: {input_frame.iloc[0][feature]}")

    prediction = int(model.predict(input_frame)[0])
    interpretation = "probable acierto" if prediction == 1 else "probable fallo"

    print("\nResultado")
    print(f"Prediccion numerica: {prediction}")
    print(f"Interpretacion: {interpretation}")

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(input_frame)
        failure_prob = probability_for_class(model, probabilities, 0)
        success_prob = probability_for_class(model, probabilities, 1)
        if success_prob is not None:
            print(f"Probabilidad de acierto: {success_prob:.4f}")
        if failure_prob is not None:
            print(f"Probabilidad de fallo: {failure_prob:.4f}")
    else:
        print("Advertencia: el modelo no soporta predict_proba().")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
