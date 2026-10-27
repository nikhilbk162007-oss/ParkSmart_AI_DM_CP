"""Generate and validate reproducible, explicitly synthetic occupancy data."""

import argparse
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


DATA_SOURCE = "synthetic-demo-v1"
REQUIRED_COLUMNS = (
    "parking_id",
    "timestamp",
    "total_capacity",
    "occupied_spaces",
    "data_source",
)

DEFAULT_START_TIME = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)
DEFAULT_CAPACITY_RANGE = (80, 400)
_TWO_PI = 2.0 * math.pi


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return isinstance(value, float) and math.isnan(value)


def _parse_aware_timestamp(value: Any, row_number: int) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        timestamp_text = value.strip()
        if timestamp_text.endswith("Z"):
            timestamp_text = timestamp_text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(timestamp_text)
        except ValueError as exc:
            raise ValueError(
                "Row {} has an invalid ISO-8601 timestamp: {!r}".format(
                    row_number, value
                )
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
    return parsed


def validate_dataset(rows: Iterable[Mapping[str, Any]]) -> None:
    """Validate dataset rows without modifying or repairing their values.

    Timestamps may be timezone-aware ``datetime`` objects or ISO-8601 strings.
    Rows representing the same instant are considered duplicates, even if their
    timezone offsets differ.
    """
    seen_observations = set()
    row_count = 0

    for row_number, row in enumerate(rows, start=1):
        row_count += 1
        if not isinstance(row, Mapping):
            raise ValueError("Row {} must be a mapping of column names to values".format(row_number))

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in row]
        if missing_columns:
            raise ValueError(
                "Row {} is missing required columns: {}".format(
                    row_number, ", ".join(missing_columns)
                )
            )

        for column in REQUIRED_COLUMNS:
            if _is_missing(row[column]):
                raise ValueError(
                    "Row {} has a missing value for {!r}".format(row_number, column)
                )

        parking_id = row["parking_id"]
        if not isinstance(parking_id, str) or not parking_id.strip():
            raise ValueError(
                "Row {} parking_id must be a non-empty string".format(row_number)
            )

        timestamp = _parse_aware_timestamp(row["timestamp"], row_number)
        observation_key = (parking_id, timestamp.astimezone(timezone.utc))
        if observation_key in seen_observations:
            raise ValueError(
                "Row {} duplicates parking_id/timestamp observation for {!r}".format(
                    row_number, parking_id
                )
            )
        seen_observations.add(observation_key)

        capacity = row["total_capacity"]
        if type(capacity) is not int or capacity < 0:
            raise ValueError(
                "Row {} total_capacity must be a non-negative integer".format(
                    row_number
                )
            )

        occupied = row["occupied_spaces"]
        if type(occupied) is not int:
            raise ValueError(
                "Row {} occupied_spaces must be an integer".format(row_number)
            )
        if occupied < 0 or occupied > capacity:
            raise ValueError(
                "Row {} occupied_spaces must be between 0 and total_capacity ({})".format(
                    row_number, capacity
                )
            )

        if row["data_source"] != DATA_SOURCE:
            raise ValueError(
                "Row {} data_source must be {!r} to identify synthetic data".format(
                    row_number, DATA_SOURCE
                )
            )

    if row_count == 0:
        raise ValueError("Dataset must contain at least one observation")


def _validate_positive_integer(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError("{} must be a positive integer".format(name))


def _occupancy_ratio(timestamp: datetime, rng: random.Random) -> float:
    """Return a seeded synthetic ratio using only timestamp and random noise."""
    hour = timestamp.hour
    weekday = timestamp.weekday()

    # Synthetic daily peak in the early afternoon and lower overnight demand.
    daily_pattern = 0.52 + 0.18 * math.cos(_TWO_PI * (hour - 14) / 24.0)
    weekday_adjustment = 0.08 if weekday < 5 else -0.08
    seeded_variation = rng.uniform(-0.07, 0.07)
    return max(0.08, min(0.92, daily_pattern + weekday_adjustment + seeded_variation))


def generate_synthetic_dataset(
    facility_count: int = 5,
    observation_count: int = 168,
    start_time: Optional[datetime] = None,
    interval: timedelta = timedelta(hours=1),
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Generate synthetic observations for multiple facilities.

    ``observation_count`` is the number of hourly (by default) observations per
    facility. ``start_time`` must be timezone-aware; generated timestamps are
    normalized to UTC. The default window begins at 2026-01-05 00:00 UTC.
    """
    _validate_positive_integer(facility_count, "facility_count")
    _validate_positive_integer(observation_count, "observation_count")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not isinstance(interval, timedelta) or interval.total_seconds() <= 0:
        raise ValueError("interval must be a positive timedelta")

    if start_time is None:
        start_time = DEFAULT_START_TIME
    if not isinstance(start_time, datetime):
        raise ValueError("start_time must be a timezone-aware datetime")
    if start_time.tzinfo is None or start_time.utcoffset() is None:
        raise ValueError("start_time must include a timezone offset")
    start_time = start_time.astimezone(timezone.utc)

    rng = random.Random(seed)
    rows = []
    for facility_index in range(1, facility_count + 1):
        capacity = rng.randint(*DEFAULT_CAPACITY_RANGE)
        parking_id = "synthetic-facility-{:03d}".format(facility_index)

        for observation_index in range(observation_count):
            timestamp = start_time + observation_index * interval
            ratio = _occupancy_ratio(timestamp, rng)
            occupied = int(capacity * ratio + 0.5)
            occupied = max(0, min(capacity, occupied))
            rows.append(
                {
                    "parking_id": parking_id,
                    "timestamp": timestamp,
                    "total_capacity": capacity,
                    "occupied_spaces": occupied,
                    "data_source": DATA_SOURCE,
                }
            )

    validate_dataset(rows)
    return rows


def write_dataset_csv(
    rows: Sequence[Mapping[str, Any]], output_path: Any
) -> None:
    """Validate rows and write them as CSV with timezone-bearing ISO timestamps."""
    validate_dataset(rows)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for row in rows:
            timestamp = _parse_aware_timestamp(row["timestamp"], 1)
            csv_row = {column: row[column] for column in REQUIRED_COLUMNS}
            csv_row["timestamp"] = timestamp.isoformat()
            writer.writerow(csv_row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate explicitly synthetic ParkSmart occupancy observations."
    )
    parser.add_argument("--output", required=True, help="Destination CSV path")
    parser.add_argument("--facility-count", type=int, default=5)
    parser.add_argument("--observation-count", type=int, default=168)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = generate_synthetic_dataset(
        facility_count=args.facility_count,
        observation_count=args.observation_count,
        seed=args.seed,
    )
    write_dataset_csv(rows, args.output)
    print(
        "Wrote {} synthetic observations to {}".format(len(rows), args.output)
    )


if __name__ == "__main__":
    main()
