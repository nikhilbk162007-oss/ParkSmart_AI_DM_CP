from datetime import datetime, timedelta, timezone
import joblib
import pytest

from ml_model import predict, training
from ml_model.training import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MIN_SAMPLES_LEAF,
    DEFAULT_N_ESTIMATORS,
    FEATURE_NAMES,
    build_feature_vector,
)


class StubEstimator:
    def __init__(self, value=42.4, error=None):
        self.value = value
        self.error = error
        self.n_features_in_ = len(FEATURE_NAMES)
        self.received_features = None

    def predict(self, feature_rows):
        if self.error is not None:
            raise self.error
        self.received_features = feature_rows
        return [self.value]


def _bundle(model=None):
    return {
        "model": model or StubEstimator(),
        "feature_names": list(FEATURE_NAMES),
        "data_source": "synthetic-demo-v1",
        "settings": {
            "n_estimators": DEFAULT_N_ESTIMATORS,
            "max_depth": DEFAULT_MAX_DEPTH,
            "min_samples_leaf": DEFAULT_MIN_SAMPLES_LEAF,
            "random_state": 42,
            "n_jobs": 1,
        },
    }


def _bundle_without_feature_order():
    bundle = _bundle()
    bundle["feature_names"] = ["hour_sin", "total_capacity"]
    return bundle


def _request(capacity=100, target_time="2026-01-05T12:00:00Z"):
    return {
        "parking_data": {"id": "facility-example", "totalCapacity": capacity},
        "target_time": target_time,
    }


def test_backend_keyword_call_returns_required_fields(monkeypatch):
    estimator = StubEstimator(value=42.4)
    monkeypatch.setattr(predict, "_load_model", lambda: estimator)

    result = predict.predict_occupancy(
        parking_data={"id": "facility-example", "totalCapacity": 100},
        target_time="2026-01-05T12:00:00Z",
    )

    assert result == {
        "predictedOccupiedSpaces": 42,
        "modelSource": predict.MODEL_SOURCE,
    }
    assert result["modelSource"] == "random-forest-regressor-v1-synthetic-demo"


def test_prediction_zero_capacity_returns_zero_after_artifact_validation(monkeypatch):
    estimator = StubEstimator()
    monkeypatch.setattr(predict, "_load_model", lambda: estimator)

    result = predict.predict_occupancy(**_request(capacity=0))

    assert result["predictedOccupiedSpaces"] == 0
    assert result["modelSource"] == predict.MODEL_SOURCE
    assert estimator.received_features is None


@pytest.mark.parametrize(
    "raw_value,expected",
    [(4.49, 4), (4.5, 5), (-1.0, 0), (11.0, 10)],
)
def test_predictions_are_rounded_and_bounded(raw_value, expected, monkeypatch):
    monkeypatch.setattr(
        predict, "_load_model", lambda: StubEstimator(value=raw_value)
    )

    result = predict.predict_occupancy(**_request(capacity=10))

    assert type(result["predictedOccupiedSpaces"]) is int
    assert result["predictedOccupiedSpaces"] == expected
    assert 0 <= result["predictedOccupiedSpaces"] <= 10


@pytest.mark.parametrize(
    "parking_data",
    [
        None,
        [],
        {"totalCapacity": 10},
        {"id": "", "totalCapacity": 10},
        {"id": "x"},
        {"id": "x", "totalCapacity": True},
        {"id": "x", "totalCapacity": -1},
        {"id": "x", "totalCapacity": 1.5},
        {"id": "x", "totalCapacity": float("nan")},
    ],
)
def test_invalid_parking_data_is_rejected(parking_data):
    with pytest.raises(predict.PredictionError, match="Invalid prediction input"):
        predict.predict_occupancy(
            parking_data=parking_data,
            target_time="2026-01-05T12:00:00Z",
        )


@pytest.mark.parametrize(
    "target_time",
    [
        None,
        123,
        "",
        "2026-01-05",
        "not-a-timestamp",
        "2026-01-05T12:00:00+invalid",
    ],
)
def test_invalid_target_time_is_rejected(target_time):
    with pytest.raises(predict.PredictionError, match="Invalid prediction input"):
        predict.predict_occupancy(**_request(target_time=target_time))


def test_feature_order_matches_training_and_uses_utc_normalization(monkeypatch):
    estimator = StubEstimator(value=25)
    monkeypatch.setattr(predict, "_load_model", lambda: estimator)
    offset_time = datetime(
        2026,
        1,
        5,
        17,
        30,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    predict.predict_occupancy(
        parking_data={"id": "ignored-id", "totalCapacity": 75},
        target_time=offset_time,
    )

    expected = build_feature_vector(
        75, datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    )
    assert estimator.received_features == [expected]
    assert len(estimator.received_features[0]) == len(FEATURE_NAMES)


def test_naive_datetime_and_utc_iso_timestamp_produce_same_features(monkeypatch):
    estimator = StubEstimator(value=10)
    monkeypatch.setattr(predict, "_load_model", lambda: estimator)

    naive_result = predict.predict_occupancy(
        parking_data={"id": "one", "totalCapacity": 100},
        target_time=datetime(2026, 1, 5, 12, 0),
    )
    naive_features = estimator.received_features
    utc_result = predict.predict_occupancy(
        parking_data={"id": "another", "totalCapacity": 100},
        target_time="2026-01-05T12:00:00Z",
    )

    assert estimator.received_features == naive_features
    assert naive_result == utc_result


def test_missing_artifact_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.setattr(predict, "ARTIFACT_PATH", tmp_path / "missing.joblib")

    with pytest.raises(predict.PredictionError, match="artifact was not found"):
        predict.predict_occupancy(**_request())


def test_corrupt_artifact_fails_clearly(tmp_path, monkeypatch):
    artifact_path = tmp_path / "corrupt.joblib"
    artifact_path.write_bytes(b"not a joblib model")
    monkeypatch.setattr(predict, "ARTIFACT_PATH", artifact_path)

    with pytest.raises(predict.PredictionError, match="Could not load"):
        predict.predict_occupancy(**_request())


@pytest.mark.parametrize(
    "bundle",
    [
        {},
        _bundle_without_feature_order(),
        _bundle(),
    ],
)
def test_incompatible_artifact_fails_without_fallback(
    bundle, tmp_path, monkeypatch
):
    artifact_path = tmp_path / "incompatible.joblib"
    joblib.dump(bundle, artifact_path)
    monkeypatch.setattr(predict, "ARTIFACT_PATH", artifact_path)

    with pytest.raises(predict.PredictionError):
        predict.predict_occupancy(**_request())


def test_prediction_failure_does_not_fall_back_to_fake_result(monkeypatch):
    monkeypatch.setattr(
        predict,
        "_load_model",
        lambda: StubEstimator(error=RuntimeError("estimator failed")),
    )

    with pytest.raises(predict.PredictionError, match="prediction failed"):
        predict.predict_occupancy(**_request())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_model_output_fails_clearly(value, monkeypatch):
    monkeypatch.setattr(
        predict, "_load_model", lambda: StubEstimator(value=value)
    )

    with pytest.raises(predict.PredictionError, match="non-finite"):
        predict.predict_occupancy(**_request())


def test_artifact_loader_rejects_incompatible_feature_count(tmp_path, monkeypatch):
    model = training._random_forest_regressor(random_state=42)
    model.fit([[0.0] * (len(FEATURE_NAMES) - 1)], [1])
    artifact_path = tmp_path / "wrong_feature_count.joblib"
    joblib.dump(_bundle(model), artifact_path)
    monkeypatch.setattr(predict, "ARTIFACT_PATH", artifact_path)

    with pytest.raises(predict.PredictionError, match="expects"):
        predict._load_model()
