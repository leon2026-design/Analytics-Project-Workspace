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


"""Data cleaning and feature engineering"""


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

    # 3. Harmonize column names across 2024/2025 schemas before normalization
    #    Apply a case-insensitive rename using a curated mapping, then normalize.
    rename_map = {
        # === Common identifiers ===
        "district": "odot_district",
        "odot_district_cd": "odot_district",
        "odotdistrict": "odot_district",
        "odot_dist": "odot_district",
        "odotdistrictcd": "odot_district",

        # === Segment geometry & classification ===
        # (present from 2020+)
        "length": "section_length_nbr",
        "sectionlength": "section_length_nbr",
        "section length": "section_length_nbr",
        "totlanes": "total_lanes_nbr",
        "totallanes": "total_lanes_nbr",
        "lanes": "total_lanes_nbr",
        "width": "lane_width_nbr",
        "lane width": "lane_width_nbr",
        "capacity": "capacity_nbr",
        "cap": "capacity_nbr",
        "funclass": "functional_class_cd",
        "primarysys": "primary_system_cd",

        # === Speed metrics ===
        "post spd": "posted_speed_nbr",
        "postspd": "posted_speed_nbr",
        "posted_speed": "posted_speed_nbr",
        "ff spd": "ff_speed_nbr",
        "ffspd": "ff_speed_nbr",
        "freeflowspd": "ff_speed_nbr",

        # === Volume / traffic metrics ===
        "totvolume": "total_volume_nbr",
        "totalvolume": "total_volume_nbr",
        "truckvolume": "truck_volume_nbr",
        "truck vol": "truck_volume_nbr",
        "vmt": "vmt_nbr",
        "truckvmt": "truck_vmt_nbr",
        "trkvmt": "truck_vmt_nbr",
        "volperlane": "volume_per_lane_nbr",

        # === Ratios / congestion ===
        "vcratio": "volume_capacity_ratio_nbr",
        "conindex": "congestion_index_nbr",
        "cong delay": "congestion_delay_nbr",
        "congdelay": "congestion_delay_nbr",
        "delayratio": "delay_ratio_nbr",

        # === Delay components (2020–2023 only) ===
        "phys delay": "physical_delay_nbr",
        "spdlm delay": "speed_limit_delay_nbr",
        "speedlimdelay": "speed_limit_delay_nbr",

        # === Vehicle-hours, peak data ===
        "vht": "vht_nbr",
        "peakhour": "peak_hour_nbr",
        "peak hour": "peak_hour_nbr",

        # === Growth rates (introduced 2024+) ===
        "cargrowrate": "car_growth_nbr",
        "car_growth_rate": "car_growth_nbr",
        "car_growth": "car_growth_nbr",
        "truckgrowrate": "truck_growth_nbr",
        "truck_growth_rate": "truck_growth_nbr",
        "truck_growth": "truck_growth_nbr",

        # === Route identifiers ===
        "route_type": "route_type",
        "rte_type": "route_type",
        "routetype": "route_type",
        "route_nbr": "route_nbr",
        "routenbr": "route_nbr",
        "rte_nbr": "route_nbr",

        # === Misc. additional compatibility (2025 additions) ===
        "capacitynbr": "capacity_nbr",
        "totalvolumenbr": "total_volume_nbr",
        "truckvolumenbr": "truck_volume_nbr",
        "vhtnbr": "vht_nbr",
        "vcrationbr": "volume_capacity_ratio_nbr",
        "congestionindex": "congestion_index_nbr",
        "delayrationbr": "delay_ratio_nbr",

        # === Legacy variants ===
        "fwy/art": "fwy_art_nbr",
    }
    # Build a mapping from actual column name -> standardized name using lowercase key matching
    lower_to_actual = {str(c).strip().lower(): c for c in df.columns}
    actual_renames = {}
    for k, v in rename_map.items():
        if k in lower_to_actual:
            actual_renames[lower_to_actual[k]] = v
    if actual_renames:
        df = df.rename(columns=actual_renames)

    # 4. Standardize column names (lowercase, underscores)
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
                  two_digit_year_pivot: int = 30,
                  use_merged_2024_2025: bool = True,
                  **read_csv_kwargs) -> pd.DataFrame:
    """Load and concatenate multiple CSVs.

    Args:
        path_or_pattern: directory path or glob pattern (if contains *)
        file_pattern: if a directory is passed, this pattern is joined to the dir
        year_regex: optional regex to extract a year from filename and add as `year` column
        add_source: whether to add a `source_file` column with the basename
        use_merged_2024_2025: if True, use CMS_D6_2024_2025_merged.csv instead of separate 2024/2025 files
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
    
    # Exclude files if using merged 2024-2025
    if use_merged_2024_2025:
        merged_file = os.path.join(os.path.dirname(pattern) if os.path.dirname(pattern) else ".", "CMS_D6_2024_2025_merged.csv")
        if os.path.exists(merged_file):
            # Exclude original 2024/2025 files and synthetic 2026
            exclude_patterns = ['24CarGrowthData', 'CMS_2025.csv', 'CMS_2026.csv']
            files = [f for f in files if not any(ex in os.path.basename(f) for ex in exclude_patterns)]
            # Add merged file only if not already in list
            if merged_file not in files:
                files.append(merged_file)

    frames = []
    year_re = re.compile(year_regex) if year_regex else None
    for f in files:
        df = load_data(f, **read_csv_kwargs)
        df = clean_data(df)
        if add_source:
            df["source_file"] = os.path.basename(f)
        
        # Special handling for merged 2024-2025 file which contains both years
        base = os.path.basename(f)
        if 'merged' in base.lower() and '2024' in base and '2025' in base:
            # This file contains 2024 data (from 24CarGrowthData(CMS5).csv)
            # matched to 2025 CMS format structure
            df['year'] = 2024
            # The file has CAR_GROWTH_NBR for 2024 values
            frames.append(df)
            continue
        
        if year_re:
            stem, _ext = os.path.splitext(base)
            m = year_re.search(stem)
            year_val: Optional[int] = None
            if m:
                try:
                    year_val = int(m.group(0))
                except Exception:
                    year_val = None
            # Fallback 1: two-digit year at start of filename (e.g., "24Something.csv")
            if year_val is None:
                m_start = re.match(r"^(\d{2})(?!\d)", stem)
                if m_start:
                    try:
                        yy = int(m_start.group(1))
                        century = 2000 if yy <= two_digit_year_pivot else 1900
                        year_val = century + yy
                    except Exception:
                        year_val = None
            # Fallback 2: first standalone two-digit token anywhere
            if year_val is None:
                m2 = re.search(r"(?<!\d)(\d{2})(?!\d)", stem)
                if m2:
                    try:
                        yy = int(m2.group(1))
                        century = 2000 if yy <= two_digit_year_pivot else 1900
                        year_val = century + yy
                    except Exception:
                        year_val = None
            if year_val is not None:
                df["year"] = year_val
            else:
                # Optional: leave year missing if not inferrable; training can impute or ignore
                pass
        frames.append(df)

    # concat, aligning columns
    out = pd.concat(frames, ignore_index=True, sort=False)

    # Inject 2024 CMS5 → 2025 CMS Car Growth matching before lag feature creation
    try:
        if {"year", "source_file"}.issubset(out.columns):
            # Identify 2024 and 2025 subsets
            df24_mask = out["year"] == 2024
            df25_mask = out["year"] == 2025
            if df24_mask.any() and df25_mask.any():
                df24 = out[df24_mask].copy()
                df25 = out[df25_mask].copy()

                # Only attempt match if expected key columns exist
                required_24 = {"jcrl", "a"}
                required_25 = {"route_nbr"}
                if required_24.issubset(df24.columns) and required_25.issubset(df25.columns):
                    df24_matched = match_cms5_to_cms(df24, df25)

                    if "matched_nlfid" in df24_matched.columns:
                        out.loc[df24_mask, "nlfid"] = df24_matched["matched_nlfid"].values
    except Exception:
        # Fail quietly; if mapping cannot be applied, downstream logic still works
        pass

    # Create lagged features only after normalization, rename harmonization, and year extraction have completed.
    out = _add_lag_features(out)
    return out


def _add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Attach lagged features once all schema harmonization steps are complete."""
    try:
        if "nlfid" in df.columns and "year" in df.columns:
            df = df.sort_values(["nlfid", "year"])  # stable sort for lag computation
            if "car_growth_nbr" in df.columns:
                df["car_growth_lag1"] = df.groupby("nlfid")["car_growth_nbr"].shift(1)
                grouped_car_growth = df.groupby("nlfid")["car_growth_nbr"]
                df["car_growth_roll2"] = grouped_car_growth.transform(
                    lambda series: series.rolling(window=2, min_periods=2).mean()
                )
                df["car_growth_roll3"] = grouped_car_growth.transform(
                    lambda series: series.rolling(window=3, min_periods=3).mean()
                )
            if "total_volume_nbr" in df.columns:
                df["total_volume_lag1"] = df.groupby("nlfid")["total_volume_nbr"].shift(1)
        # Always add normalized year features when year is available
        if "year" in df.columns:
            year_min = df["year"].min()
            year_span = max(1, df["year"].max() - year_min)
            df["year_norm"] = (df["year"] - year_min) / float(year_span)
            df["year_poly2"] = df["year_norm"] ** 2
    except Exception:
        # Fail silently; downstream code can proceed without lags if an unexpected issue occurs
        return df
    return df


def recompute_2026_time_features(
    df_all: pd.DataFrame,
    df_2026: pd.DataFrame,
) -> pd.DataFrame:
    """Recompute time-based features for 2026 rows only.

    This uses the same min/max year range that the model was
    trained on (i.e., derived from df_all) and applies the
    resulting normalization only to the provided 2026 slice.

    Args:
        df_all: Multi-year dataframe representing the training-era
            year distribution (e.g., 2019–2025). Must contain a
            numeric ``year`` column.
        df_2026: DataFrame containing rows with ``year == 2026``
            for which ``year_norm`` and ``year_poly2`` should be
            recomputed.

    Returns:
        A copy of ``df_2026`` with updated ``year_norm`` and
        ``year_poly2`` columns. If inputs are missing a ``year``
        column, the original ``df_2026`` is returned unchanged.
    """

    if "year" not in df_all.columns or "year" not in df_2026.columns:
        return df_2026

    df_2026 = df_2026.copy()

    # Use only the historical range (training-era years) to define
    # the normalization, preserving the model's learned scale.
    hist = df_all[df_all["year"] <= 2025]
    if hist.empty:
        hist = df_all

    year_min = hist["year"].min()
    year_span = max(1, hist["year"].max() - year_min)

    df_2026["year_norm"] = (df_2026["year"] - year_min) / float(year_span)
    df_2026["year_poly2"] = df_2026["year_norm"] ** 2
    return df_2026


if __name__ == "__main__":
    # Example usage (update filename as needed)
    data_path = "backend/data/CMS (Car Growth Rate)(CMS (Car Growth Rate)).csv"
    df = get_preprocessed_data(data_path)
    print(df.head())
    print(f"Dataset shape: {df.shape}")


def match_cms5_to_cms(df24, df25):
    """
    Match CMS5 'grid' rows (2024) to CMS Car Growth rows (2025) using:
      - route decoded from JCRL (characters 4–6 → route system code, last 5 digits → route number)
      - normalized linear position A / max(A) per route
      - nearest-neighbor match to 2025 normalized logmile
    Returns df24 with an added 'matched_nlfid' column.
    """

    import pandas as pd
    import numpy as np

    # Normalize columns
    df24 = df24.copy()
    df25 = df25.copy()

    # 1. Decode route from JCRL (supports IR, US, SR, CR, etc.)
    def decode_route(jcrl):
        """
        Extract (route_type, route_nbr) from JCRL.
        Works for IR, US, SR, CR, etc.
        Example: SWOOUS00006**C17505  ("US", 6)
                 SWOOIR00070**C30120  ("IR", 70)
        """
        if not isinstance(jcrl, str):
            return (None, None)

        import re
        # Find letters followed by exactly 5 digits
        m = re.search(r'([A-Z]+)(\d{5})', jcrl)
        if not m:
            return (None, None)

        route_type = m.group(1)      # e.g., US, SR, IR
        try:
            route_nbr = int(m.group(2))  # last 5 digits  route number
        except:
            return (None, None)

        return (route_type, route_nbr)

    df24["route_id"] = df24["jcrl"].apply(decode_route)

    # 2. Compute normalized linear position for 2024 using A column
    df24["linpos24"] = df24.groupby("route_id")["a"].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) if (x.max() > x.min()) else 0
    )

    # 3. Compute normalized linear position for 2025 using LOGMILE (or similar if available)
    logmile_col = None
    for c in df25.columns:
        if "mile" in c or "logmile" in c:
            logmile_col = c
            break
    if logmile_col is None:
        raise ValueError("2025 file must contain a mile/logmile column for mapping.")

    df25["linpos25"] = df25.groupby("route_nbr")[logmile_col].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) if (x.max() > x.min()) else 0
    )

    # 4. For each 2024 row, match to nearest 2025 row with same route_type/route_nbr
    matched_ids = []
    for _, row in df24.iterrows():
        r = row["route_id"]
        if pd.isna(r):
            matched_ids.append(None)
            continue
        route_type, route_nbr = r
        subset = df25[
            (df25["route_type"].astype(str).str.upper() == route_type)
            & (df25["route_nbr"] == route_nbr)
        ]
        if subset.empty:
            matched_ids.append(None)
            continue
        # compute absolute diff in normalized positions
        diffs = (subset["linpos25"] - row["linpos24"]).abs()
        idx = diffs.idxmin()
        matched_ids.append(df25.loc[idx, "kdot_nlfid"] if "kdot_nlfid" in df25.columns else df25.loc[idx, "unique_id"])

    df24["matched_nlfid"] = matched_ids
    return df24