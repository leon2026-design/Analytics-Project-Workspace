"""backend.preprocessing

Utilities to load, clean and prepare ODOT/CMS traffic CSVs for modeling.
This module provides helpers to load single or multiple CSV files, normalize
column names, coerce numeric types, validate a simple schema, and persist
processed datasets. It is intended to be used by training and prediction code
in the backend.
"""

import os
from typing import Optional

import pandas as pd


"""Data cleaning and feature engineering stubs"""


def load_data(file_path: str, **read_csv_kwargs) -> pd.DataFrame:
    """Load raw traffic dataset from CSV.

    Allows passing read_csv like parse_dates, encoding, etc.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    return pd.read_csv(file_path, low_memory=False, **read_csv_kwargs)


def clean_data(df: pd.DataFrame, fill_strategy: Optional[str] = "median") -> pd.DataFrame:
    """Clean and preprocess traffic dataset.

    Args:
        df: input dataframe
        fill_strategy: "zero" | "median" | "mean"
    """
    # work on a copy to avoid SettingWithCopyWarning and side-effects
    df = df.copy()

    # 1. Drop completely empty columns
    df = df.dropna(axis=1, how="all")

    # 2. Fill missing numeric values (use a broader numeric selector)
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if fill_strategy == "median":
        df.loc[:, numeric_cols] = df.loc[:, numeric_cols].fillna(df.loc[:, numeric_cols].median())
    elif fill_strategy == "mean":
        df.loc[:, numeric_cols] = df.loc[:, numeric_cols].fillna(df.loc[:, numeric_cols].mean())
    else:
        df.loc[:, numeric_cols] = df.loc[:, numeric_cols].fillna(0)

    # 3. Standardize column names (lowercase, underscores)
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    return df


# Backwards-compatible alias
def clean(df: pd.DataFrame) -> pd.DataFrame:
    return clean_data(df)


def get_preprocessed_data(file_path: str, **read_csv_kwargs) -> pd.DataFrame:
    """Load and clean data."""
    raw_df = load_data(file_path, **read_csv_kwargs)
    clean_df = clean_data(raw_df)
    return clean_df


def validate_schema(df: pd.DataFrame, required_columns: Optional[list] = None) -> None:
    """Validate presence of required columns. Raises ValueError if missing.

    Args:
        df: dataframe to check
        required_columns: list of required column names (before normalization)
    """
    if not required_columns:
        return
    # normalize required column names the same way we normalize df columns
    normalized = [str(c).strip().lower().replace(" ", "_") for c in required_columns]
    missing = [c for c in normalized if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def coerce_numeric(df: pd.DataFrame, columns: Optional[list] = None, errors: str = "coerce") -> pd.DataFrame:
    """Coerce specified columns (or all object columns) to numeric.

    Args:
        df: dataframe to operate on (will return a copy)
        columns: list of column names to coerce. If None, will attempt to coerce all object dtype columns.
        errors: behaviour passed to `pd.to_numeric`
    Returns:
        DataFrame copy with coerced columns.
    """
    df = df.copy()
    if columns is None:
        candidates = df.select_dtypes(include=["object"]).columns.tolist()
    else:
        candidates = columns
    for col in candidates:
        try:
            df[col] = pd.to_numeric(df[col], errors=errors)
        except Exception:
            # leave as-is if conversion fails
            pass
    return df


def save_processed(df: pd.DataFrame, out_path: str, index: bool = False) -> None:
    """Save processed dataframe to CSV, creating parent dirs if needed."""
    parent = os.path.dirname(out_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    df.to_csv(out_path, index=index)


def load_all_data(path_or_pattern: str = "backend/data", file_pattern: str = "*.csv",
                  year_regex: Optional[str] = r"(19|20)\d{2}", add_source: bool = True,
                  **read_csv_kwargs) -> pd.DataFrame:
    """Load and concatenate multiple CSVs.

    Args:
        path_or_pattern: directory path or glob pattern (if contains *)
        file_pattern: if a directory is passed, this pattern is joined to the dir
        year_regex: optional regex to extract a year from filename and add as `year` column
        add_source: whether to add a `source_file` column with the basename
        read_csv_kwargs: passed to read_csv
    Returns:
        concatenated cleaned DataFrame
    """
    import glob
    import re

    # build glob pattern
    if os.path.isdir(path_or_pattern):
        pattern = os.path.join(path_or_pattern, file_pattern)
    else:
        pattern = path_or_pattern

    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matched pattern: {pattern}")

    frames = []
    year_re = re.compile(year_regex) if year_regex else None
    for f in files:
        df = load_data(f, **read_csv_kwargs)
        df = clean_data(df)
        if add_source:
            df["source_file"] = os.path.basename(f)
        if year_re:
            m = year_re.search(os.path.basename(f))
            if m:
                # take the full match (e.g., 2025)
                try:
                    df["year"] = int(m.group(0))
                except Exception:
                    pass
        frames.append(df)

    # concat, aligning columns
    out = pd.concat(frames, ignore_index=True, sort=False)
    return out


if __name__ == "__main__":
    # Example usage (update filename as needed)
    data_path = "backend/data/CMS (Car Growth Rate)(CMS (Car Growth Rate)).csv"
    df = get_preprocessed_data(data_path)
    print(df.head())
    print(f"Dataset shape: {df.shape}")