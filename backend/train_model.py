"""backend.train_model

Simple training script for the Columbus Traffic Predictor backend. Loads
preprocessed traffic data, trains a baseline sklearn regression pipeline
(imputer, scaler, linear regression), evaluates basic metrics, saves the
trained pipeline and records metadata about the training run.
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from backend.preprocessing import (
    get_preprocessed_data,
    coerce_numeric,
    validate_schema,
    load_all_data,
)

# Paths
DATA_PATH = "backend/data"  # directory or pattern; can point to a single CSV too
MODEL_DIR = "backend/models"
MODEL_PATH = os.path.join(MODEL_DIR, "traffic_model.pkl")

# Features/target
TARGET = "car_growth_nbr"
FEATURES = [
    "posted_speed_nbr",
    "total_lanes_nbr",
    "capacity_nbr",
    "total_volume_nbr",
    "truck_volume_nbr",
]


def train_model(data_path: str = DATA_PATH, model_path: str = MODEL_PATH):
    # 1. Load and preprocess data (supports directory or glob)
    if os.path.isdir(data_path) or ("*" in data_path):
        df = load_all_data(data_path)
    else:
        df = get_preprocessed_data(data_path)

    # Persist cleaned concatenated dataset for reproducibility
    processed_dir = os.path.join("backend", "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    processed_path = os.path.join(processed_dir, "traffic_all_clean.csv")
    # save using the helper if available
    try:
        from backend.preprocessing import save_processed

        save_processed(df, processed_path)
    except Exception:
        df.to_csv(processed_path, index=False)

    # 2. Ensure schema + numeric and coerce
    validate_schema(df, required_columns=[TARGET] + FEATURES)
    df = coerce_numeric(df, FEATURES + [TARGET])

    # 2b. Drop rows with missing target or features
    df = df.dropna(subset=[TARGET] + FEATURES)

    # 3. Define X, y
    X = df[FEATURES]
    y = df[TARGET]

    # 4. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Build pipeline and train
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("lr", LinearRegression()),
    ])
    pipeline.fit(X_train, y_train)

    # 6. Evaluate
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"✅ Model trained. MAE={mae:.3f}, R²={r2:.3f}")

    # 7. Save model + metadata
    os.makedirs(MODEL_DIR, exist_ok=True)
    meta = {"features": FEATURES, "target": TARGET, "mae": mae, "r2": r2}
    joblib.dump({"model": pipeline, "meta": meta}, model_path)
    print(f"📁 Model and metadata saved to {model_path}")

    # Append run to training_runs.csv
    runs_path = os.path.join(MODEL_DIR, "training_runs.csv")
    import csv
    from datetime import datetime

    run_row = {
        "timestamp": datetime.utcnow().isoformat(),
        "data_path": data_path,
        "processed_path": processed_path,
        "model_path": model_path,
        "features": ";".join(FEATURES),
        "target": TARGET,
        "mae": mae,
        "r2": r2,
    }

    file_exists = os.path.exists(runs_path)
    with open(runs_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(run_row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(run_row)

    return pipeline


def train(data_path: str = DATA_PATH, model_path: str = MODEL_PATH):
    """Backwards-compatible function used by tests."""
    train_model(data_path, model_path)


if __name__ == "__main__":
    train_model()

