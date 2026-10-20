# PRD 3: AI/ML Parking Occupancy Prediction

## Project
**ParkSmart AI — AI-Based Smart Parking Recommendation System**

## Objective
Build and evaluate a model that estimates parking occupancy for a target time and exposes a consistent prediction interface.

## Responsibilities
- Find or generate a documented occupancy dataset.
- Clean and validate data using Pandas.
- Explore features such as time of day, day of week, capacity, and historical occupancy when available.
- Create a reproducible train/test split.
- Train a baseline and a Random Forest Regressor if suitable.
- Evaluate with Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
- Save the model and preprocessing steps if needed.
- Implement a prediction function with documented inputs and outputs.
- Explain data limitations and whether the dataset is real or simulated.

## Proposed Technology
Python, Pandas, scikit-learn, and optionally Joblib and Jupyter Notebook.

## Dataset Documentation
Document the source or generation method, column meanings and units, record count, missing-value handling, features, target, split method, assumptions, and limitations.

Avoid data leakage: input features must not reveal the target directly or indirectly.

## Prediction Contract
Coordinate with the backend member on a function such as:

```python
predict_occupancy(parking_data, target_time)
```

Specify whether the result is occupied spaces, an occupancy percentage, or both. Use one consistent definition across the project.

If the model predicts occupied spaces:

`predicted_free_spaces = total_capacity - predicted_occupied_spaces`

Validate or clamp predictions to sensible capacity bounds and document rounding.

## Evaluation
- Compare against a simple baseline.
- Report MAE and RMSE on held-out data.
- Document test-set size and split approach.
- Do not use training performance as evidence of generalization.
- Do not claim real-world accuracy if only simulated data is used.

## Deliverables
- Dataset or reproducible data-generation script.
- Cleaning and training code.
- Saved model artifact if required.
- Prediction function.
- Evaluation results and limitations.
- Setup instructions in `ml-model/README.md`.

## Acceptance Criteria
- Training and evaluation are reproducible.
- Features and target are documented.
- Model is compared with a baseline.
- MAE and RMSE are reported on held-out data.
- Output follows the shared team contract.
- Real and simulated data are clearly distinguished.

## Dependencies
Backend confirms the input/output schema; recommendation member defines how predictions are used; frontend needs accurate labels for predicted values.
