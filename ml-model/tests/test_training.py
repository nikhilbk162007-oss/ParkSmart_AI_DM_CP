import math
from datetime import datetime, timezone

import pytest

from ml_model.dataset import DATA_SOURCE, generate_synthetic_dataset
from ml_model import training
from ml_model.training import (
    OptionalDependencyError,
    calculate_metrics,
    capacity_scaled_mean_baseline,
    chronological_split,
    occupancy_count,
    train_and_evaluate,
)


def _small_rows():
    rows = []
    for facility_id, capacity in (
        ("synthetic-facility-001", 100),
        ("synthetic-facility-002", 200),
    ):
        for hour in range(10):
            timestamp = datetime(2026, 1, 5, hour, tzinfo=timezone.utc)
            ratio = 0.2 + 0.05 * hour
            rows.append(
                {
                    "parking_id": facility_id,
                    "timestamp": timestamp,
                    "total_capacity": capacity,
                    "occupied_spaces": int(capacity * ratio + 0.5),
                    "data_source": DATA_SOURCE,
                }
            )
    return rows


def test_chronological_split_keeps_all_facilities_at_each_timestamp_together():
    train_rows, test_rows = chronological_split(_small_rows(), test_fraction=0.2)
    train_times = {row["timestamp"] for row in train_rows}
    test_times = {row["timestamp"] for row in test_rows}

    assert train_times.isdisjoint(test_times)
    assert max(train_times) < min(test_times)
    assert len(train_rows) == 16
    assert len(test_rows) == 4
    assert all(
        sum(row["timestamp"] == timestamp for row in train_rows) == 2
        for timestamp in train_times
    )
    assert all(
        sum(row["timestamp"] == timestamp for row in test_rows) == 2
        for timestamp in test_times
    )


def test_chronological_split_rejects_too_few_timestamps_and_invalid_fraction():
    rows = _small_rows()
    first_timestamp = rows[0]["timestamp"]
    one_timestamp = [
        row for row in rows if row["timestamp"] == first_timestamp
    ]
    with pytest.raises(ValueError, match="At least two distinct timestamps"):
        chronological_split(one_timestamp)

    with pytest.raises(ValueError, match="test_fraction"):
        chronological_split(_small_rows(), test_fraction=1.0)


def test_baseline_metric_correctness_on_hand_calculated_example():
    training_rows = [
        {
            "total_capacity": 100,
            "occupied_spaces": 20,
        },
        {
            "total_capacity": 200,
            "occupied_spaces": 40,
        },
    ]
    test_rows = [
        {"total_capacity": 150},
        {"total_capacity": 300},
    ]

    baseline_predictions = capacity_scaled_mean_baseline(training_rows, test_rows)
    metrics = calculate_metrics([30, 60], baseline_predictions)

    assert baseline_predictions == [30.0, 60.0]
    assert metrics == {"mae": 0.0, "rmse": 0.0}


def test_baseline_metrics_match_hand_calculated_values():
    training_rows = [{"total_capacity": 100, "occupied_spaces": 50}]
    test_rows = [{"total_capacity": 100}, {"total_capacity": 200}]
    baseline_predictions = capacity_scaled_mean_baseline(training_rows, test_rows)

    assert baseline_predictions == [50.0, 100.0]
    assert calculate_metrics([60, 80], baseline_predictions) == {
        "mae": 15.0,
        "rmse": pytest.approx(math.sqrt(250.0)),
    }


def test_mae_and_rmse_are_correct_for_exact_and_constant_errors():
    assert calculate_metrics([1, 2, 3], [1, 2, 3]) == {
        "mae": 0.0,
        "rmse": 0.0,
    }
    assert calculate_metrics([10, 10, 10], [8, 10, 14]) == {
        "mae": 2.0,
        "rmse": pytest.approx(math.sqrt(20.0 / 3.0)),
    }


@pytest.mark.parametrize(
    "actual,predicted",
    [
        ([], []),
        ([1], []),
        ([float("nan")], [1]),
        ([1], [float("inf")]),
        ([True], [1]),
        ([1], ["not numeric"]),
    ],
)
def test_metrics_reject_empty_mismatched_or_nonfinite_inputs(actual, predicted):
    with pytest.raises(ValueError):
        calculate_metrics(actual, predicted)


@pytest.mark.parametrize(
    "prediction,capacity,expected",
    [
        (4.49, 10, 4),
        (4.5, 10, 5),
        (-2.0, 10, 0),
        (12.0, 10, 10),
        (12.0, 0, 0),
    ],
)
def test_occupancy_count_rounds_half_up_and_enforces_capacity(
    prediction, capacity, expected
):
    assert occupancy_count(prediction, capacity) == expected


def test_occupancy_count_rejects_invalid_capacity_and_prediction():
    with pytest.raises(ValueError, match="total_capacity"):
        occupancy_count(1.0, -1)
    with pytest.raises(ValueError, match="raw_prediction"):
        occupancy_count(float("nan"), 10)


def test_training_metrics_are_reproducible_with_fixed_seed():
    rows = generate_synthetic_dataset(
        facility_count=3, observation_count=48, seed=17
    )
    first = train_and_evaluate(rows=rows, seed=17)
    second = train_and_evaluate(rows=rows, seed=17)

    assert first.metrics == second.metrics
    assert first.metrics["data_source"] == DATA_SOURCE
    assert first.metrics["split"]["train_samples"] + first.metrics["split"]["test_samples"] == len(rows)


def test_training_reports_finite_baseline_and_random_forest_metrics():
    result = train_and_evaluate(
        facility_count=3, observation_count=48, seed=23
    )

    for approach in ("baseline", "random_forest"):
        for output_type in ("raw_regression", "rounded_bounded_counts"):
            metrics = result.metrics[approach][output_type]
            assert math.isfinite(metrics["mae"])
            assert math.isfinite(metrics["rmse"])
            assert metrics["mae"] >= 0
            assert metrics["rmse"] >= 0


def test_training_rejects_rows_with_non_synthetic_provenance():
    rows = _small_rows()
    rows[0] = dict(rows[0], data_source="real-observation")

    with pytest.raises(ValueError, match="data_source must be"):
        train_and_evaluate(rows=rows)


def test_random_forest_dependency_failure_is_explicit(monkeypatch):
    original_import = __import__

    def import_without_sklearn(name, *args, **kwargs):
        if name == "sklearn.ensemble":
            raise ImportError("simulated missing scikit-learn")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", import_without_sklearn)
    with pytest.raises(OptionalDependencyError, match="requires scikit-learn"):
        training._random_forest_regressor(random_state=42)
