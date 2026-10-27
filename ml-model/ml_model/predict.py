"""Backend-compatible occupancy predictions from the trained synthetic model."""

import math
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from .dataset import DATA_SOURCE
from .training import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MIN_SAMPLES_LEAF,
    DEFAULT_N_ESTIMATORS,
    FEATURE_NAMES,
    build_feature_vector,
    occupancy_count,
)


ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent
    / "artifacts"
    / "occupancy_random_forest.joblib"
)
MODEL_SOURCE = "random-forest-regressor-v1-synthetic-demo"


class PredictionError(RuntimeError):
    """Raised when an occupancy prediction cannot be safely produced."""


def _parse_target_time(value: Union[datetime, str]) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        timestamp_text = value.strip()
        if "T" not in timestamp_text and " " not in timestamp_text:
            raise ValueError("target_time must include an ISO-8601 date and time")
        if timestamp_text.endswith("Z"):
            timestamp_text = timestamp_text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(timestamp_text)
        except ValueError as exc:
            raise ValueError("target_time is not a valid ISO-8601 datetime") from exc
    else:
        raise ValueError("target_time must be a datetime or ISO-8601 string")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        # The backend may send naive datetimes; this model interprets them as UTC.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_request(
    parking_data: Any, target_time: Any
) -> Tuple[int, datetime]:
    if not isinstance(parking_data, Mapping):
        raise ValueError("parking_data must be a mapping")
    if "id" not in parking_data:
        raise ValueError("parking_data must contain an 'id' value")
    parking_id = parking_data["id"]
    if not isinstance(parking_id, str) or not parking_id.strip():
        raise ValueError("parking_data['id'] must be a non-empty string")
    if "totalCapacity" not in parking_data:
        raise ValueError("parking_data must contain 'totalCapacity'")

    total_capacity = parking_data["totalCapacity"]
    if type(total_capacity) is not int or total_capacity < 0:
        raise ValueError("parking_data['totalCapacity'] must be a non-negative integer")

    parsed_time = _parse_target_time(target_time)
    return total_capacity, parsed_time


def _load_model(artifact_path: Optional[Path] = None) -> Any:
    if artifact_path is None:
        artifact_path = ARTIFACT_PATH
    if not artifact_path.is_file():
        raise PredictionError(
            "Random Forest model artifact was not found at {}".format(artifact_path)
        )

    try:
        import joblib
    except ImportError as exc:
        raise PredictionError(
            "Loading the Random Forest artifact requires joblib and scikit-learn "
            "in the active Python environment"
        ) from exc

    try:
        bundle = joblib.load(artifact_path)
    except Exception as exc:
        raise PredictionError(
            "Could not load Random Forest model artifact at {}".format(artifact_path)
        ) from exc

    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise PredictionError(
            "Loading the Random Forest artifact requires scikit-learn"
        ) from exc

    if not isinstance(bundle, Mapping):
        raise PredictionError("Model artifact must contain a metadata mapping")

    feature_names = bundle.get("feature_names")
    if not isinstance(feature_names, (list, tuple)) or tuple(feature_names) != FEATURE_NAMES:
        raise PredictionError(
            "Model artifact feature order is incompatible with this package"
        )
    if bundle.get("data_source") != DATA_SOURCE:
        raise PredictionError(
            "Model artifact provenance is missing or is not synthetic demo data"
        )

    settings = bundle.get("settings")
    expected_settings = {
        "n_estimators": DEFAULT_N_ESTIMATORS,
        "max_depth": DEFAULT_MAX_DEPTH,
        "min_samples_leaf": DEFAULT_MIN_SAMPLES_LEAF,
        "n_jobs": 1,
    }
    if not isinstance(settings, Mapping):
        raise PredictionError("Model artifact is missing training settings")
    for key, expected_value in expected_settings.items():
        if settings.get(key) != expected_value:
            raise PredictionError(
                "Model artifact setting {!r} is incompatible".format(key)
            )
    random_state = settings.get("random_state")
    if type(random_state) is not int or not 0 <= random_state <= 2**32 - 1:
        raise PredictionError("Model artifact has an invalid random_state")

    model = bundle.get("model")
    if not isinstance(model, RandomForestRegressor):
        raise PredictionError(
            "Model artifact does not contain a RandomForestRegressor"
        )
    feature_count = getattr(model, "n_features_in_", len(FEATURE_NAMES))
    if feature_count != len(FEATURE_NAMES):
        raise PredictionError(
            "Model artifact expects {} features; {} are required".format(
                feature_count, len(FEATURE_NAMES)
            )
        )
    return model


def predict_occupancy(
    parking_data: Dict[str, Any],
    target_time: Union[datetime, str],
) -> Dict[str, Union[int, str]]:
    """Predict occupied spaces using the packaged Random Forest artifact.

    Naive datetimes are interpreted as UTC. Timezone-aware datetimes and
    ISO-8601 strings are normalized to UTC before deriving model features.
    Parking ID is validated for the backend contract but is never a feature.
    """
    try:
        total_capacity, utc_target_time = _validate_request(
            parking_data, target_time
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise PredictionError("Invalid prediction input: {}".format(exc)) from exc

    model = _load_model()
    if total_capacity == 0:
        return {
            "predictedOccupiedSpaces": 0,
            "modelSource": MODEL_SOURCE,
        }

    feature_vector = build_feature_vector(total_capacity, utc_target_time)
    try:
        raw_predictions = model.predict([feature_vector])
        if len(raw_predictions) != 1:
            raise ValueError("estimator must return exactly one prediction")
        raw_prediction = float(raw_predictions[0])
    except Exception as exc:
        raise PredictionError("Random Forest prediction failed") from exc

    if not math.isfinite(raw_prediction):
        raise PredictionError("Random Forest returned a non-finite prediction")

    return {
        "predictedOccupiedSpaces": occupancy_count(
            raw_prediction, total_capacity
        ),
        "modelSource": MODEL_SOURCE,
    }
