"""backend.train_model

Training script for the Columbus Traffic Predictor backend. Loads preprocessed
traffic data, trains an imputed XGBoost regression pipeline, evaluates holdout
metrics, saves the trained pipeline, and records metadata about the run.
"""

import os
from pathlib import Path
from typing import Optional
import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor
import matplotlib.pyplot as plt
import numpy as np

from backend.core.preprocessing import (
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
    "ff_speed_nbr",
    "total_lanes_nbr",
    "lane_width_nbr",
    "capacity_nbr",
    "total_volume_nbr",
    "truck_volume_nbr",
    "vmt_nbr",
    "truck_vmt_nbr",
    "vht_nbr",
    "volume_capacity_ratio_nbr",
    "congestion_index_nbr",
    "congestion_delay_nbr",
    "delay_ratio_nbr",
    "section_length_nbr",
    "median_width_nbr",
    "fwy_art_nbr",
    "year",
]


def train_model(data_path: str = DATA_PATH, model_path: str = MODEL_PATH, odot_district: Optional[int] = 6):
    # 1. Load and preprocess data (supports directory or glob)
    if os.path.isdir(data_path) or ("*" in data_path):
        df = load_all_data(data_path)
    else:
        df = get_preprocessed_data(data_path)

    # filter dataset to specific ODOT district to Columbus = 6
    if odot_district is not None:
        col = "odot_district"
        if col in df.columns:
            # coerce to numeric for safe comparison
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except Exception:
                pass
            before = len(df)
            df = df[df[col] == odot_district]
            after = len(df)
            print(f"Filtered by {col}={odot_district}: {before} -> {after} rows")
        else:
            print(f"Warning: column '{col}' not found in data; skipping district filter")

    # Persist cleaned concatenated dataset for reproducibility
    processed_dir = os.path.join("backend", "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    processed_path = os.path.join(processed_dir, "traffic_all_clean.csv")
    # save using the helper if available
    try:
        from backend.core.preprocessing import save_processed

        save_processed(df, processed_path)
    except Exception:
        df.to_csv(processed_path, index=False)

    # 2. Ensure schema + numeric and coerce
    available_features = [f for f in FEATURES if f in df.columns]
    missing_features = [f for f in FEATURES if f not in df.columns]
    if missing_features:
        print(f"Warning: missing features will be ignored: {missing_features}")
    if not available_features:
        raise ValueError("No requested FEATURES are present in the dataset after preprocessing.")

    validate_schema(df, required_columns=[TARGET] + available_features)
    df = coerce_numeric(df, available_features + [TARGET])

    # 2b. Drop rows with missing target only; let the imputer handle missing features
    df = df.dropna(subset=[TARGET])

    # 3. Year restriction (keep only rows >=2019 to reduce drift/noise from older years)
    if "year" in df.columns:
        yr_num_tmp = pd.to_numeric(df["year"], errors="coerce")
        before_year_filter = len(df)
        df = df[yr_num_tmp >= 2019]
        after_year_filter = len(df)
        if after_year_filter == 0:
            raise ValueError("All rows removed by year >=2019 filter; check year parsing.")
        # Optional log
        print(f"Year filter >=2019: {before_year_filter} -> {after_year_filter} rows")

    # 4. Random 80/20 split (matching historical best model approach)
    from sklearn.model_selection import train_test_split
    
    X = df[available_features]
    y = df[TARGET]
    
    # Random 80/20 split with fixed seed for reproducibility
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"Random 80/20 split: train={len(X_train)}, test={len(X_test)}")
    
    # Sample weights based on year (if year is in features)
    if "year" in df.columns:
        year_numeric = pd.to_numeric(df["year"], errors="coerce")
        df["sample_weight"] = year_numeric - 2016
        w_train = df.loc[X_train.index, "sample_weight"].to_numpy()
    else:
        w_train = None

    # 5. Build pipeline and train
    # Hyperparameters optimized via GridSearchCV (2025-12-06)
    # Tuning improved R² from 0.646 to 0.883 (+36.5%)
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb", XGBRegressor(
            n_estimators=500,
            learning_rate=0.07,      # Tuned: 0.05 → 0.07
            max_depth=7,             # Tuned: 6 → 7
            subsample=0.8,           # Optimal (unchanged)
            colsample_bytree=0.5,    # Tuned: 0.8 → 0.5 (addresses multicollinearity)
            reg_lambda=1.25,         # Tuned: 1.0 → 1.25
            random_state=42,
            n_jobs=-1,
            tree_method="hist",
        )),
    ])
    # Fit without early stopping to avoid eval_set transformation mismatch in Pipeline
    pipeline.fit(X_train, y_train, xgb__sample_weight=w_train)

    # 6. Evaluate
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"Model trained. MAE={mae:.3f}, R²={r2:.3f}")

    # 7. Save model + metadata
    os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
    meta = {"features": available_features, "target": TARGET, "mae": mae, "r2": r2}
    joblib.dump({"model": pipeline, "meta": meta}, model_path)
    print(f"Model and metadata saved to {model_path}")

    # 7b. Export feature importances (XGBRegressor)
    try:
        xgb = pipeline.named_steps.get("xgb")
        if xgb is not None and hasattr(xgb, "feature_importances_"):
            importances = np.array(xgb.feature_importances_, dtype=float)
            names = list(available_features)
            # Try to use model's view of feature names/count when possible
            model_names = None
            if hasattr(xgb, "feature_names_in_"):
                try:
                    model_names = list(xgb.feature_names_in_)
                except Exception:
                    model_names = None
            if model_names and len(model_names) == len(importances):
                names = model_names
            # Align lengths defensively
            if len(names) != len(importances):
                if len(names) > len(importances):
                    names = names[: len(importances)]
                else:
                    # pad synthetic names if fewer names than importances
                    pad = [f"feat_{i}" for i in range(len(importances) - len(names))]
                    names = names + pad
            fi_dir = Path(MODEL_DIR)
            fi_dir.mkdir(parents=True, exist_ok=True)
            # Save CSV
            fi_df = pd.DataFrame({
                "feature": names,
                "importance": importances,
            }).sort_values("importance", ascending=False)
            fi_csv_path = fi_dir / "feature_importances.csv"
            fi_df.to_csv(fi_csv_path, index=False)
            # Save bar plot (top 20)
            top_k = min(20, len(fi_df))
            top_df = fi_df.head(top_k)[::-1]  # reverse for horizontal plot
            plt.figure(figsize=(8, max(4, 0.35 * top_k + 1)))
            plt.barh(top_df["feature"], top_df["importance"], color="#2a9d8f")
            plt.xlabel("Importance")
            plt.title("XGBoost Feature Importances (top 20)")
            plt.tight_layout()
            fi_png_path = fi_dir / "feature_importances.png"
            plt.savefig(fi_png_path, dpi=150)
            plt.close()
            print(f"Feature importances saved: {fi_csv_path} and {fi_png_path}")
        else:
            print("Note: Feature importances not available on the final estimator.")
    except Exception as e:
        print(f"Warning: failed to export feature importances: {e}")

    # Append run to training_runs.csv
    runs_path = os.path.join(MODEL_DIR, "training_runs.csv")
    import csv
    from datetime import datetime

    run_row = {
        "timestamp": datetime.utcnow().isoformat(),
        "data_path": data_path,
        "processed_path": processed_path,
        "model_path": model_path,
        "features": ";".join(available_features),
        "target": TARGET,
        "odot_district": odot_district,
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


def train(
    data_path: str = DATA_PATH,
    model_path: str = MODEL_PATH,
    odot_district: Optional[int] = 6,
):
    """Backwards-compatible function used by tests."""
    return train_model(data_path, model_path, odot_district)


if __name__ == "__main__":
    # Train only on ODOT district 6 (Columbus area) by default
    train_model(odot_district=6)
