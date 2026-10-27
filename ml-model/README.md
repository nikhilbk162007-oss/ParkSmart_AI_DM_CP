# ParkSmart AI ML component — Stages 1–3

The ML component provides an importable `ml_model` package, reproducible
synthetic occupancy data, a chronological baseline/Random Forest training and
evaluation workflow, and a backend-compatible inference function.

## Dataset status and assumptions

The generated records are synthetic demo data, **not a real parking dataset or
real-world measurements**. They are produced from documented assumptions to
support reproducible development and later pipeline testing.

- Each facility receives a seeded capacity from 80 through 400 spaces.
- The default output has five facilities and 168 hourly observations per
  facility, starting at 2026-01-05 00:00 UTC.
- Occupancy follows a deterministic daily pattern with an early-afternoon peak,
  a weekday/weekend adjustment, and seeded random variation.
- The pattern uses only timestamp-derived hour/day-of-week and capacity when
  converting a ratio to a count. `parking_id` identifies a facility but is not
  used as a predictive feature.
- Generated timestamps are timezone-aware and normalized to UTC. CSV timestamps
  include the UTC offset.
- The fixed provenance field is `synthetic-demo-v1` on every generated row.

This is a simple demonstration generator, not a statistically validated model of
parking demand. Its patterns are assumptions chosen for predictable examples.
Metrics measured on generated data would measure agreement with those generator
assumptions; **they cannot establish real-world prediction accuracy**.

## Columns and units

| Column | Meaning |
|---|---|
| `parking_id` | Synthetic facility identifier; not a predictive feature |
| `timestamp` | Observation time as a timezone-aware UTC datetime / ISO-8601 CSV value |
| `total_capacity` | Capacity as a whole number of spaces |
| `occupied_spaces` | Synthetic occupied-space count; integer spaces from zero through capacity |
| `data_source` | Synthetic provenance label, always `synthetic-demo-v1` |

`occupied_spaces` is the intended future model target. Candidate features
available at inference are `total_capacity` and features derived from
`target_time`, such as hour of day and day of week. The dataset does not include
historical sensor readings or real facility-specific behavior.

## Reproducibility and generation

The generator uses Python's standard library only. It defaults to seed `42`;
the facility count, number of observations per facility, starting timestamp,
observation interval, and seed can also be supplied through the Python API:

```python
from datetime import datetime, timezone
from ml_model.dataset import generate_synthetic_dataset, write_dataset_csv

rows = generate_synthetic_dataset(
    facility_count=5,
    observation_count=168,
    start_time=datetime(2026, 1, 5, tzinfo=timezone.utc),
    seed=42,
)
write_dataset_csv(rows, "data/synthetic_occupancy.csv")
```

From this directory, generate a default-sized CSV with:

```powershell
python -m ml_model.dataset --output data\synthetic_occupancy.csv --seed 42
```

The command creates the output directory if needed. Reusing the same seed and
configuration produces identical rows. Changing the seed changes capacities
and/or seeded occupancy variation.

## Stage 2 training and evaluation

Training requires `scikit-learn`; saving the fitted model requires `joblib`.
These runtime dependencies are declared in `pyproject.toml`. The package
requires Python 3.11 or later and constrains scikit-learn to the 1.8 release
series to match the existing model artifact's recorded scikit-learn version.
Tests require `pytest`, which is not an ML package runtime dependency.

For backend development, the backend requirements should include
`-e ../ml-model`. From `backend/`, install the backend requirements with:

```powershell
python -m pip install -r requirements.txt
```

This editable install makes `ml_model` importable to the backend and installs
the ML package's declared runtime dependencies. The editable install keeps
Python loading the package from `ml-model/ml_model/`, so the current artifact
path at `ml-model/artifacts/occupancy_random_forest.joblib` remains available.
This assumes the source checkout remains present.

The current setup is not a self-contained wheel distribution: the model
artifact is outside the Python package and is not included in a wheel. A wheel
deployment would require packaging the artifact as package data and updating
the loader to resolve it from the installed package.

From this directory, the reproducible default workflow is:

```powershell
python -m ml_model.training --facility-count 5 --observation-count 168 --seed 42 --test-fraction 0.2
```

This command creates `artifacts\occupancy_random_forest.joblib` and
`artifacts\evaluation.json` beneath `ml-model/`; the output directory can be
changed only to another location beneath `ml-model/`. The report records the
synthetic provenance, seed, split ranges and sample counts, feature names,
model settings, and metrics. The training module can also be called directly:

```python
from ml_model.training import train_and_evaluate

result = train_and_evaluate(
    facility_count=5,
    observation_count=168,
    test_fraction=0.2,
    seed=42,
)
print(result.metrics)
```

### Split, features, baseline, and metrics

- The split is chronological across all facilities at one shared timestamp
  boundary. All facility observations at a timestamp go into the same
  partition. Earlier timestamps train the model; the latest portion is held
  out for testing. This prevents a timestamp from being in both sets and avoids
  training on later times than the held-out observations.
- Model features are capacity plus UTC hour-of-day and weekday sine/cosine
  encodings. Facility ID, provenance, observed occupancy, and any target-derived
  values are excluded as predictors.
- The baseline calculates the aggregate occupied/capacity ratio over training
  rows and multiplies that ratio by each test facility's capacity.
- The Random Forest uses 100 trees, maximum depth 8, minimum leaf size 2,
  `random_state` equal to the selected seed, and one worker. These settings are
  fixed and documented for repeatable runs.
- Raw regression MAE and RMSE are measured in spaces before rounding or
  capacity bounding. Separate metrics are also reported after converting
  predictions to whole-space counts.
- Count conversion rounds half-up (`floor(value + 0.5)`) and clamps to
  `[0, total_capacity]`. Zero-capacity facilities produce zero occupied spaces.
- MAE and RMSE are computed on the held-out rows. The report includes both
  training and test sample counts and their UTC timestamp ranges.

These are synthetic-data demonstration results, **not evidence of real-world
accuracy**. The baseline and model are evaluated against generated values from
the same assumed pattern; results cannot establish performance on actual
parking occupancy.

## Stage 3 inference API

The synchronous inference function is `ml_model.predict.predict_occupancy` and
accepts the keyword arguments used by the backend module adapter:

```python
from ml_model.predict import predict_occupancy

result = predict_occupancy(
    parking_data={"id": "fixture-riverfront", "totalCapacity": 420},
    target_time="2026-10-25T14:30:00+05:30",
)
```

`parking_data` must contain a non-empty string `id` and a non-negative integer
`totalCapacity` (booleans are rejected). `target_time` may be a Python
`datetime` or an ISO-8601 date-time string. Timezone-aware values are converted
to UTC. Naive datetime values and strings are explicitly interpreted as UTC,
matching the synthetic model's documented time basis. Parking ID is validated
for the backend contract but is never used as a model feature.

The returned mapping contains:

```python
{
    "predictedOccupiedSpaces": 286,  # integer, bounded by totalCapacity
    "modelSource": "random-forest-regressor-v1-synthetic-demo",
}
```

The backend adapter derives free spaces and occupancy percentage from the
occupied count and facility capacity; the ML function therefore does not return
duplicate derived fields. For zero capacity, it returns zero occupied spaces
after successfully loading and validating the model artifact. Fractional model
outputs are rounded half-up and then clamped to `[0, totalCapacity]`.

The model artifact must exist at `ml-model/artifacts/occupancy_random_forest.joblib`
relative to the package. Its stored feature order, synthetic provenance,
training settings, and estimator feature count are checked before use. `joblib`
and scikit-learn must be available in the active Python environment. Missing,
corrupt, incompatible artifacts and estimator failures raise `PredictionError`;
there is no mock or baseline fallback.

The model was trained using synthetic demonstration data only. Its provenance
label must not be interpreted as a real-world prediction or accuracy claim.
The backend must be configured to use its `module` adapter mode, and the
`ml-model` package must be installed in that backend Python environment. Its
current backend requirements need the coordinated `-e ../ml-model` entry.

## Validation rules

`validate_dataset(rows)` raises `ValueError` with a row-specific message rather
than repairing invalid records. It checks that:

- Every row contains the required columns and non-missing values.
- `parking_id` is a non-empty string.
- Timestamps parse as ISO-8601 or are datetime values with a timezone offset.
- A facility has no duplicate observation for the same instant (equivalent
  instants with different offsets are also duplicates).
- `total_capacity` is a non-negative integer and `occupied_spaces` is an integer
  in `[0, total_capacity]`. Booleans and fractional values are rejected.
- `data_source` is exactly `synthetic-demo-v1`.
- The dataset contains at least one observation.

Naive timestamps are rejected because their timezone is ambiguous. The generator
also rejects a naive `start_time` and converts aware starting times to UTC.

## Tests

The tests use `pytest` in addition to the package runtime dependencies. After
installing the backend requirements (including the editable ML package) and
ensuring pytest is available, run from this directory:

```powershell
python -m pytest -q
```

The dataset-only Stage 1 pipeline uses standard-library APIs and typing syntax
compatible with Python 3.8 and later. The installable ML package requires
Python 3.11 or later because the selected scikit-learn 1.8 release requires
that runtime; confirm this aligns with the backend's deployment runtime.

## Limitations

- Data is synthetic and encodes an assumed daily/weekly pattern; it is not
  evidence of demand at actual facilities.
- There are no real historical observations, sensor readings, traffic signals,
  event calendars, holidays, or facility-specific predictive features.
- The generated facility IDs are identifiers only and must not be used by a
  model as predictive features.
- A random seed makes this generator reproducible but does not make its
  assumptions representative.
- Training and evaluation on this synthetic data do not establish real-world
  accuracy.
- The Stage 3 `ml_model.predict.predict_occupancy(parking_data=..., target_time=...)`
  interface and package-relative artifact loading are implemented. The model
  was trained and evaluated only on synthetic demonstration data and has not
  been validated for real-world parking predictions.
- Backend integration still requires a compatible runtime environment with
  `scikit-learn` and `joblib` available. The backend requirements must include
  the local editable package for the ML module to be importable.
