"""Chronological baseline and Random Forest evaluation for synthetic data."""

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .dataset import (
    DATA_SOURCE,
    generate_synthetic_dataset,
    validate_dataset,
)


FEATURE_NAMES = (
    "total_capacity",
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
)
DEFAULT_TEST_FRACTION = 0.2
DEFAULT_RANDOM_STATE = 42
DEFAULT_N_ESTIMATORS = 100
DEFAULT_MAX_DEPTH = 8
DEFAULT_MIN_SAMPLES_LEAF = 2
ML_MODEL_ROOT = Path(__file__).resolve().parents[1]


class OptionalDependencyError(RuntimeError):
    """Raised when optional model or artifact dependencies are unavailable."""


@dataclass
class TrainingResult:
    """Held-out evaluation summary and fitted model."""

    metrics: Dict[str, Any]
    model: Any


def _parse_timestamp(value: Any, row_number: int) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(
                "Row {} has an invalid timestamp".format(row_number)
            ) from exc
    else:
        raise ValueError(
            "Row {} timestamp must be a datetime or ISO-8601 string".format(
                row_number
            )
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            "Row {} timestamp must include a timezone offset".format(row_number)
        )
    return parsed.astimezone(timezone.utc)


def chronological_split(
    rows: Sequence[Mapping[str, Any]],
    test_fraction: float = DEFAULT_TEST_FRACTION,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    """Split all facilities at common chronological timestamp boundaries.

    Every row for a timestamp is assigned to the same partition. The earliest
    timestamps form the training set; the latest timestamps form the held-out
    test set. This prevents a facility's later observations from being used to
    train against another facility's earlier test observations.
    """
    validate_dataset(rows)
    if isinstance(test_fraction, bool) or not isinstance(test_fraction, (int, float)):
        raise ValueError("test_fraction must be a number between 0 and 1")
    if not math.isfinite(float(test_fraction)) or not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be a finite number between 0 and 1")

    timestamped_rows = [
        (_parse_timestamp(row["timestamp"], row_number), row)
        for row_number, row in enumerate(rows, start=1)
    ]
    distinct_timestamps = sorted({timestamp for timestamp, _ in timestamped_rows})
    if len(distinct_timestamps) < 2:
        raise ValueError("At least two distinct timestamps are required for a chronological split")

    split_index = int(math.floor(len(distinct_timestamps) * (1.0 - test_fraction)))
    if split_index < 1 or split_index >= len(distinct_timestamps):
        raise ValueError(
            "test_fraction leaves an empty training or test timestamp range"
        )

    cutoff = distinct_timestamps[split_index]
    ordered_rows = sorted(
        timestamped_rows,
        key=lambda item: (item[0], item[1]["parking_id"]),
    )
    train_rows = [row for timestamp, row in ordered_rows if timestamp < cutoff]
    test_rows = [row for timestamp, row in ordered_rows if timestamp >= cutoff]

    if not train_rows or not test_rows:
        raise ValueError("Chronological split must contain training and test rows")
    return train_rows, test_rows


def build_feature_vector(total_capacity: int, target_time: Any) -> List[float]:
    """Build model features in the exact order stored with the trained artifact."""
    timestamp = _parse_timestamp(target_time, 1)
    hour = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0
    weekday = timestamp.weekday()
    return [
        float(total_capacity),
        math.sin(2.0 * math.pi * hour / 24.0),
        math.cos(2.0 * math.pi * hour / 24.0),
        math.sin(2.0 * math.pi * weekday / 7.0),
        math.cos(2.0 * math.pi * weekday / 7.0),
    ]


def calculate_metrics(
    actual: Sequence[float], predicted: Sequence[float]
) -> Dict[str, float]:
    """Calculate finite MAE and RMSE for non-empty, equal-length sequences."""
    if len(actual) == 0:
        raise ValueError("actual and predicted values must not be empty")
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted values must have equal lengths")

    errors = []
    for actual_value, predicted_value in zip(actual, predicted):
        if isinstance(actual_value, bool) or isinstance(predicted_value, bool):
            raise ValueError("metric values must be finite numbers")
        try:
            actual_number = float(actual_value)
            predicted_number = float(predicted_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("metric values must be finite numbers") from exc
        if not math.isfinite(actual_number) or not math.isfinite(predicted_number):
            raise ValueError("metric values must be finite numbers")
        errors.append(predicted_number - actual_number)

    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    if not math.isfinite(mae) or not math.isfinite(rmse):
        raise ValueError("calculated metrics must be finite")
    return {"mae": mae, "rmse": rmse}


def capacity_scaled_mean_baseline(
    training_rows: Sequence[Mapping[str, Any]],
    prediction_rows: Sequence[Mapping[str, Any]],
) -> List[float]:
    """Predict the training aggregate occupancy ratio times each lot's capacity."""
    total_capacity = sum(row["total_capacity"] for row in training_rows)
    if total_capacity <= 0:
        raise ValueError("Training data must include positive total capacity")
    occupancy_ratio = sum(
        row["occupied_spaces"] for row in training_rows
    ) / float(total_capacity)
    return [
        occupancy_ratio * row["total_capacity"] for row in prediction_rows
    ]


def occupancy_count(raw_prediction: float, total_capacity: int) -> int:
    """Round half-up to a space count, then bound it to facility capacity."""
    if type(total_capacity) is not int or total_capacity < 0:
        raise ValueError("total_capacity must be a non-negative integer")
    if isinstance(raw_prediction, bool):
        raise ValueError("raw_prediction must be a finite number")
    try:
        prediction = float(raw_prediction)
    except (TypeError, ValueError) as exc:
        raise ValueError("raw_prediction must be a finite number") from exc
    if not math.isfinite(prediction):
        raise ValueError("raw_prediction must be a finite number")
    if total_capacity == 0:
        return 0
    rounded = math.floor(prediction + 0.5)
    return max(0, min(total_capacity, rounded))


def _random_forest_regressor(random_state: int) -> Any:
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise OptionalDependencyError(
            "Random Forest training requires scikit-learn. Install it in the "
            "Python environment used to run this module."
        ) from exc

    return RandomForestRegressor(
        n_estimators=DEFAULT_N_ESTIMATORS,
        max_depth=DEFAULT_MAX_DEPTH,
        min_samples_leaf=DEFAULT_MIN_SAMPLES_LEAF,
        random_state=random_state,
        n_jobs=1,
    )


def train_and_evaluate(
    rows: Optional[Sequence[Mapping[str, Any]]] = None,
    facility_count: int = 5,
    observation_count: int = 168,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    seed: int = DEFAULT_RANDOM_STATE,
) -> TrainingResult:
    """Train a Random Forest and compare it with a capacity-scaled baseline.

    All input rows must have the synthetic provenance required by the Stage 1
    dataset validator. Regression metrics use raw float predictions in spaces.
    Additional rounded-count metrics describe the bounded deployed-count form.
    """
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an integer between 0 and 4294967295")
    if rows is None:
        rows = generate_synthetic_dataset(
            facility_count=facility_count,
            observation_count=observation_count,
            seed=seed,
        )
    validate_dataset(rows)
    train_rows, test_rows = chronological_split(rows, test_fraction)

    actual = [row["occupied_spaces"] for row in test_rows]
    baseline_raw = capacity_scaled_mean_baseline(train_rows, test_rows)

    feature_rows = [
        build_feature_vector(row["total_capacity"], row["timestamp"])
        for row in train_rows
    ]
    test_features = [
        build_feature_vector(row["total_capacity"], row["timestamp"])
        for row in test_rows
    ]
    targets = [row["occupied_spaces"] for row in train_rows]

    model = _random_forest_regressor(seed)
    model.fit(feature_rows, targets)
    forest_raw = [float(value) for value in model.predict(test_features)]

    baseline_counts = [
        occupancy_count(value, row["total_capacity"])
        for value, row in zip(baseline_raw, test_rows)
    ]
    forest_counts = [
        occupancy_count(value, row["total_capacity"])
        for value, row in zip(forest_raw, test_rows)
    ]

    train_times = [_parse_timestamp(row["timestamp"], 1) for row in train_rows]
    test_times = [_parse_timestamp(row["timestamp"], 1) for row in test_rows]
    metrics = {
        "data_source": DATA_SOURCE,
        "result_label": "synthetic-data demonstration; not real-world accuracy",
        "seed": seed,
        "test_fraction": float(test_fraction),
        "features": list(FEATURE_NAMES),
        "split": {
            "method": "global chronological timestamp boundary across all facilities",
            "train_samples": len(train_rows),
            "test_samples": len(test_rows),
            "train_timestamp_start": min(train_times).isoformat(),
            "train_timestamp_end": max(train_times).isoformat(),
            "test_timestamp_start": min(test_times).isoformat(),
            "test_timestamp_end": max(test_times).isoformat(),
        },
        "baseline": {
            "description": "training-set aggregate occupancy ratio multiplied by capacity",
            "raw_regression": calculate_metrics(actual, baseline_raw),
            "rounded_bounded_counts": calculate_metrics(actual, baseline_counts),
        },
        "random_forest": {
            "settings": {
                "n_estimators": DEFAULT_N_ESTIMATORS,
                "max_depth": DEFAULT_MAX_DEPTH,
                "min_samples_leaf": DEFAULT_MIN_SAMPLES_LEAF,
                "random_state": seed,
                "n_jobs": 1,
            },
            "raw_regression": calculate_metrics(actual, forest_raw),
            "rounded_bounded_counts": calculate_metrics(actual, forest_counts),
        },
    }

    return TrainingResult(metrics=metrics, model=model)


def save_training_artifacts(
    result: TrainingResult, output_directory: Path
) -> Tuple[Path, Path]:
    """Save model and metrics JSON beneath the ml-model directory."""
    output_path = Path(output_directory).resolve()
    try:
        output_path.relative_to(ML_MODEL_ROOT)
    except ValueError as exc:
        raise ValueError(
            "Training artifacts must be saved inside the ml-model directory"
        ) from exc

    try:
        import joblib
    except ImportError as exc:
        raise OptionalDependencyError(
            "Saving the model artifact requires joblib. Install it in the "
            "Python environment used to run this module."
        ) from exc

    output_path.mkdir(parents=True, exist_ok=True)
    model_path = output_path / "occupancy_random_forest.joblib"
    metrics_path = output_path / "evaluation.json"
    joblib.dump(
        {
            "model": result.model,
            "feature_names": list(FEATURE_NAMES),
            "data_source": DATA_SOURCE,
            "settings": result.metrics["random_forest"]["settings"],
        },
        model_path,
    )
    with metrics_path.open("w", encoding="utf-8") as metrics_file:
        json.dump(result.metrics, metrics_file, indent=2, allow_nan=False)
        metrics_file.write("\n")
    return model_path, metrics_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate occupancy models on synthetic demo data."
    )
    parser.add_argument("--facility-count", type=int, default=5)
    parser.add_argument("--observation-count", type=int, default=168)
    parser.add_argument("--test-fraction", type=float, default=DEFAULT_TEST_FRACTION)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_STATE)
    parser.add_argument(
        "--output-directory",
        default=str(ML_MODEL_ROOT / "artifacts"),
        help="Directory beneath ml-model for model and evaluation outputs",
    )
    args = parser.parse_args()

    rows = generate_synthetic_dataset(
        facility_count=args.facility_count,
        observation_count=args.observation_count,
        seed=args.seed,
    )
    result = train_and_evaluate(
        rows=rows,
        test_fraction=args.test_fraction,
        seed=args.seed,
    )
    model_path, metrics_path = save_training_artifacts(
        result, Path(args.output_directory)
    )
    print(json.dumps(result.metrics, indent=2, allow_nan=False))
    print("Model artifact: {}".format(model_path))
    print("Evaluation output: {}".format(metrics_path))


if __name__ == "__main__":
    main()
