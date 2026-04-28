from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split


FEATURE_COLUMNS = [
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
TARGET_COLUMN = "matched"
REQUIRED_COLUMNS = FEATURE_COLUMNS + [TARGET_COLUMN]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a RandomForest model to predict whether a memory turn matches."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to dataset_turn_match_prediction.csv",
    )
    return parser.parse_args()


def normalize_matched(value: Any) -> int | None:
    if isinstance(value, bool):
        return 1 if value else 0
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return 1
    if text in {"false", "0", "no", "n"}:
        return 0
    return None


def load_dataset(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo CSV: {csv_path}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"La ruta no es un archivo CSV: {csv_path}")

    data = pd.read_csv(csv_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(missing))

    return data


def prepare_training_data(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, int]:
    dataset = data[REQUIRED_COLUMNS].copy()
    dataset[TARGET_COLUMN] = dataset[TARGET_COLUMN].map(normalize_matched)

    for column in FEATURE_COLUMNS:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")

    before_drop = len(dataset)
    dataset = dataset.dropna(subset=REQUIRED_COLUMNS)
    removed_rows = before_drop - len(dataset)

    x = dataset[FEATURE_COLUMNS]
    y = dataset[TARGET_COLUMN].astype(int)
    return x, y, removed_rows


def split_data(
    x: pd.DataFrame,
    y: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    try:
        return train_test_split(
            x,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )
    except ValueError as exc:
        print(
            f"Advertencia: no se pudo usar stratify ({exc}). Se usara split normal."
        )
        return train_test_split(
            x,
            y,
            test_size=0.2,
            random_state=42,
        )


def save_metadata(
    metadata_path: Path,
    csv_path: Path,
    rows_used: int,
    accuracy: float,
) -> None:
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "rows_used": rows_used,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "accuracy": accuracy,
        "model": "RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)",
        "csv_path": str(csv_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)

    try:
        data = load_dataset(csv_path)
        x, y, removed_rows = prepare_training_data(data)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Filas leidas: {len(data)}")
    print(f"Filas eliminadas por valores nulos o invalidos: {removed_rows}")
    print(f"Filas usadas para entrenamiento/evaluacion: {len(x)}")

    if len(x) < 30:
        print("Advertencia: el dataset es muy pequeño. El entrenamiento es solo demostrativo.")

    class_counts = y.value_counts().to_dict()
    print(f"Distribucion de clases: {class_counts}")

    if len(x) < 2:
        print("ERROR: se necesitan al menos 2 filas validas para entrenar.", file=sys.stderr)
        return 1
    if y.nunique() < 2:
        print("ERROR: se necesitan ejemplos de ambas clases matched=true y matched=false.", file=sys.stderr)
        return 1

    x_train, x_test, y_train, y_test = split_data(x, y)

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        max_depth=5,
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])
    report = classification_report(y_test, y_pred, zero_division=0)

    print("\nEvaluacion")
    print(f"accuracy: {accuracy:.4f}")
    print(f"precision: {precision:.4f}")
    print(f"recall: {recall:.4f}")
    print(f"f1-score: {f1:.4f}")
    print("matriz de confusion labels=[0,1]:")
    print(matrix)
    print("classification_report:")
    print(report)

    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "turn_match_model.pkl"
    metadata_path = models_dir / "turn_match_model_metadata.json"

    joblib.dump(model, model_path)
    save_metadata(metadata_path, csv_path, len(x), accuracy)

    print(f"Modelo guardado en: {model_path}")
    print(f"Metadata guardada en: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
