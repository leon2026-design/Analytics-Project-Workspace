"""backend.predict

Prediction interface for the Columbus Traffic Predictor backend.
Loads a trained sklearn pipeline from disk and produces car_growth_nbr
predictions for new data (single record or batch DataFrame).
"""

import os
import joblib
import pandas as pd
from typing import Union, Dict, Any
from sklearn.metrics import mean_absolute_error, r2_score

from backend.preprocessing import load_all_data, coerce_numeric
import numpy as np

# Default paths
MODEL_PATH = "backend/models/traffic_model.pkl"
PREDICTIONS_DIR = "backend/data/predictions"
DATA_DIR = "backend/data"

# Updated features list — same as train_model.py
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
    "year",
    "year_norm",
    "year_poly2",
]


def _infer_year_from_path(path: str) -> int | None:
    """Infer a year value from a filename using 4-digit and 2-digit heuristics."""
    base = os.path.basename(path)
    stem, _ext = os.path.splitext(base)
    import re

    year_val: int | None = None
    # First, look for a 4-digit year
    m = re.search(r"(19|20)\d{2}", stem)
    if m:
        try:
            return int(m.group(0))
        except Exception:
            year_val = None

    # Fallback: two-digit year at start of filename (e.g., "24CMS.csv")
    m_start = re.match(r"^(\d{2})(?!\d)", stem)
    if m_start:
        try:
            yy = int(m_start.group(1))
            pivot = 30
            return (2000 if yy <= pivot else 1900) + yy
        except Exception:
            year_val = None

    # Secondary fallback: first standalone two-digit token anywhere in the stem
    m2 = re.search(r"(?<!\d)(\d{2})(?!\d)", stem)
    if m2:
        try:
            yy = int(m2.group(1))
            pivot = 30
            return (2000 if yy <= pivot else 1900) + yy
        except Exception:
            year_val = None

    return year_val


def load_model(model_path: str = MODEL_PATH):
    """Load trained model and metadata."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    bundle = joblib.load(model_path)
    return bundle["model"], bundle.get("meta", {})


def _ensure_feature_columns(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Ensure all required feature columns exist; add missing as NaN and order columns.

    This lets the pipeline's imputer handle missing values at inference.
    """
    df = df.copy()
    for col in features:
        if col not in df.columns:
            # Use np.nan (not pandas.NA) so sklearn imputers handle it
            df[col] = np.nan
    # Replace any pandas.NA with np.nan to be sklearn-friendly
    df[features] = df[features].replace({pd.NA: np.nan})
    return df


def predict_from_dataframe(df: pd.DataFrame, model_path: str = MODEL_PATH) -> pd.DataFrame:
    """Generate predictions from a DataFrame.

    Args:
        df: DataFrame with the same feature columns used in training
        model_path: path to the saved model

    Returns:
        DataFrame with original features + predicted car_growth_nbr
    """
    model, meta = load_model(model_path)
    # Prefer metadata features if available
    features = meta.get("features", FEATURES)

    # Coerce numeric and ensure required columns exist (missing set to NaN)
    df = coerce_numeric(df, features)
    df = _ensure_feature_columns(df, features)

    # Run prediction (pipeline handles imputation/scaling)
    preds = model.predict(df[features])
    df["predicted_car_growth_nbr"] = preds
    return df


def predict_from_dict(data: Dict[str, Any], model_path: str = MODEL_PATH) -> float:
    """Predict car_growth_nbr from a single observation (dict of features)."""
    df = pd.DataFrame([data])
    result_df = predict_from_dataframe(df, model_path)
    return float(result_df["predicted_car_growth_nbr"].iloc[0])


def predict_from_csv(input_csv: str, output_csv: str = None, model_path: str = MODEL_PATH, odot_district: int | None = 6) -> pd.DataFrame:
    """Load a CSV, run predictions, and optionally save results."""
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    target_year = _infer_year_from_path(input_csv)

    # Use the same multi-year dataset as training so lag features remain populated
    df = load_all_data(DATA_DIR)

    if target_year is not None:
        if "year" in df.columns:
            before_year = len(df)
            df = df[df["year"] == target_year].copy()
            after_year = len(df)
            print(f"Filtered to target year {target_year}: {before_year} -> {after_year} rows")
            if after_year == 0:
                print(f"Warning: No rows found for target year {target_year} in aggregated dataset.")
        else:
            print(f"Warning: Aggregated dataset missing 'year' column; cannot filter to {target_year}.")
    else:
        print("Warning: Could not infer target year from filename; using all available years for prediction.")

    # Match training scope by default: filter to ODOT district 6 if column is present
    if odot_district is not None and "odot_district" in df.columns:
        try:
            df = coerce_numeric(df, ["odot_district"])  # safe numeric comparison
        except Exception:
            pass
        before = len(df)
        df = df[df["odot_district"] == odot_district]
        after = len(df)
        print(f"Filtered by odot_district={odot_district}: {before} -> {after} rows")
    result_df = predict_from_dataframe(df, model_path)

    # If the ground-truth target is present, compute quick validation metrics
    target_col = "car_growth_nbr"
    pred_col = "predicted_car_growth_nbr"
    if target_col in result_df.columns and pred_col in result_df.columns:
        y_true = pd.to_numeric(result_df[target_col], errors="coerce")
        y_pred = pd.to_numeric(result_df[pred_col], errors="coerce")
        mask = y_true.notna() & y_pred.notna()
        n = int(mask.sum())
        if n > 0:
            mae = mean_absolute_error(y_true[mask], y_pred[mask])
            # r2_score requires at least two samples to be meaningful
            r2 = r2_score(y_true[mask], y_pred[mask]) if n >= 2 else float('nan')
            if n >= 2:
                print(f"Validation metrics on file: MAE={mae:.3f}, R²={r2:.3f} (n={n})")
            else:
                print(f"Validation metrics on file: MAE={mae:.3f}, R²=N/A (n={n})")
        else:
            print("Warning: No valid rows to compute MAE (target/prediction NaN after coercion).")

    if output_csv:
        out_dir = os.path.dirname(output_csv)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        result_df.to_csv(output_csv, index=False)
        print(f"Predictions saved to {output_csv}")

    return result_df


if __name__ == "__main__":
    # Example usage: single prediction
    sample_input = {
        "posted_speed_nbr": 55,
        "ff_speed_nbr": 60,
        "total_lanes_nbr": 4,
        "lane_width_nbr": 12,
        "capacity_nbr": 4000,
        "total_volume_nbr": 3200,
        "truck_volume_nbr": 300,
        "vmt_nbr": 15000,
        "truck_vmt_nbr": 1200,
        "vht_nbr": 1000,
        "volume_capacity_ratio_nbr": 0.8,
        "congestion_index_nbr": 1.2,
        "congestion_delay_nbr": 200,
        "delay_ratio_nbr": 0.15,
        "section_length_nbr": 1.5,
    }
 


    # Example batch prediction on the actual CMS dataset
    in_path = "backend/data/CMS (Car Growth Rate)(CMS (Car Growth Rate)).csv"
    out_path = os.path.join(PREDICTIONS_DIR, "predicted_cms_car_growth.csv")
    predict_from_csv(in_path, out_path)
