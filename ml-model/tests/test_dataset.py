import csv
from datetime import datetime, timedelta, timezone

import pytest

from ml_model.dataset import (
    DATA_SOURCE,
    REQUIRED_COLUMNS,
    generate_synthetic_dataset,
    validate_dataset,
    write_dataset_csv,
)


def _sample_row():
    return {
        "parking_id": "synthetic-facility-001",
        "timestamp": datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
        "total_capacity": 100,
        "occupied_spaces": 60,
        "data_source": DATA_SOURCE,
    }


def test_same_seed_and_configuration_produce_identical_rows():
    options = {
        "facility_count": 3,
        "observation_count": 24,
        "start_time": datetime(2026, 1, 5, tzinfo=timezone.utc),
        "seed": 42,
    }

    assert generate_synthetic_dataset(**options) == generate_synthetic_dataset(**options)


def test_default_configuration_uses_five_facilities_and_168_hourly_observations():
    rows = generate_synthetic_dataset()

    assert len(rows) == 5 * 168
    assert len({row["parking_id"] for row in rows}) == 5
    assert rows[0]["timestamp"] == datetime(2026, 1, 5, tzinfo=timezone.utc)
    assert rows[1]["timestamp"] - rows[0]["timestamp"] == timedelta(hours=1)
    assert generate_synthetic_dataset() == generate_synthetic_dataset(seed=42)


def test_different_seeds_change_generated_variation():
    first = generate_synthetic_dataset(
        facility_count=2, observation_count=24, seed=42
    )
    second = generate_synthetic_dataset(
        facility_count=2, observation_count=24, seed=43
    )

    assert first != second


def test_generated_rows_have_required_columns_and_synthetic_provenance():
    rows = generate_synthetic_dataset(facility_count=2, observation_count=3)

    assert len(rows) == 6
    assert all(tuple(row.keys()) == REQUIRED_COLUMNS for row in rows)
    assert all(row["data_source"] == DATA_SOURCE for row in rows)
    assert all(row["parking_id"].startswith("synthetic-facility-") for row in rows)


def test_generated_occupancy_is_an_integer_within_capacity():
    rows = generate_synthetic_dataset(facility_count=4, observation_count=48)

    for row in rows:
        assert type(row["total_capacity"]) is int
        assert type(row["occupied_spaces"]) is int
        assert 0 <= row["occupied_spaces"] <= row["total_capacity"]


def test_generated_timestamps_are_timezone_aware_utc():
    rows = generate_synthetic_dataset(
        facility_count=1,
        observation_count=3,
        start_time=datetime(
            2026, 1, 5, 8, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
        ),
    )

    assert all(row["timestamp"].tzinfo == timezone.utc for row in rows)
    assert rows[0]["timestamp"] == datetime(2026, 1, 5, 2, 30, tzinfo=timezone.utc)


def test_validator_accepts_timezone_aware_iso_timestamp():
    row = _sample_row()
    row["timestamp"] = "2026-01-05T12:00:00+00:00"

    validate_dataset([row])


def test_validator_rejects_duplicate_facility_timestamp_observations():
    row = _sample_row()
    duplicate = dict(row, timestamp="2026-01-05T17:30:00+05:30")

    with pytest.raises(ValueError, match="duplicates parking_id/timestamp"):
        validate_dataset([row, duplicate])


@pytest.mark.parametrize(
    "column,value",
    [
        ("parking_id", None),
        ("timestamp", ""),
        ("total_capacity", None),
        ("occupied_spaces", None),
        ("data_source", None),
    ],
)
def test_validator_rejects_missing_required_values(column, value):
    row = _sample_row()
    row[column] = value

    with pytest.raises(ValueError, match="missing value"):
        validate_dataset([row])


def test_validator_rejects_missing_required_column():
    row = _sample_row()
    del row["data_source"]

    with pytest.raises(ValueError, match="missing required columns"):
        validate_dataset([row])


@pytest.mark.parametrize("capacity", [-1, 100.0, True, "100"])
def test_validator_rejects_invalid_capacity(capacity):
    row = _sample_row()
    row["total_capacity"] = capacity

    with pytest.raises(ValueError, match="total_capacity must be a non-negative integer"):
        validate_dataset([row])


@pytest.mark.parametrize("occupied", [-1, 101, 60.0, True, "60"])
def test_validator_rejects_invalid_occupancy(occupied):
    row = _sample_row()
    row["occupied_spaces"] = occupied

    with pytest.raises(ValueError, match="occupied_spaces"):
        validate_dataset([row])


def test_validator_rejects_non_synthetic_provenance():
    row = _sample_row()
    row["data_source"] = "real-sensor"

    with pytest.raises(ValueError, match="data_source must be"):
        validate_dataset([row])


@pytest.mark.parametrize(
    "timestamp",
    [
        "not-a-timestamp",
        "2026-01-05T12:00:00",
    ],
)
def test_validator_rejects_invalid_or_timezone_naive_timestamps(timestamp):
    row = _sample_row()
    row["timestamp"] = timestamp

    with pytest.raises(ValueError, match="timestamp"):
        validate_dataset([row])


def test_generator_rejects_timezone_naive_start_time():
    with pytest.raises(ValueError, match="start_time must include a timezone offset"):
        generate_synthetic_dataset(
            facility_count=1,
            observation_count=1,
            start_time=datetime(2026, 1, 5, 12, 0),
        )


def test_csv_writer_preserves_required_columns_and_utc_timestamps(tmp_path):
    rows = generate_synthetic_dataset(facility_count=1, observation_count=2)
    output_path = tmp_path / "synthetic.csv"

    write_dataset_csv(rows, output_path)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        written_rows = list(csv.DictReader(csv_file))

    assert tuple(written_rows[0].keys()) == REQUIRED_COLUMNS
    assert written_rows[0]["timestamp"].endswith("+00:00")
    assert all(row["data_source"] == DATA_SOURCE for row in written_rows)
    assert written_rows[0]["parking_id"] == rows[0]["parking_id"]
    assert int(written_rows[0]["total_capacity"]) == rows[0]["total_capacity"]
    assert int(written_rows[0]["occupied_spaces"]) == rows[0]["occupied_spaces"]
    parsed_rows = [
        dict(
            row,
            total_capacity=int(row["total_capacity"]),
            occupied_spaces=int(row["occupied_spaces"]),
        )
        for row in written_rows
    ]
    validate_dataset(parsed_rows)


@pytest.mark.parametrize(
    "options",
    [
        {"facility_count": 0},
        {"observation_count": 0},
        {"seed": 1.5},
        {"interval": timedelta(0)},
    ],
)
def test_generator_rejects_invalid_configuration(options):
    with pytest.raises(ValueError):
        generate_synthetic_dataset(**options)
