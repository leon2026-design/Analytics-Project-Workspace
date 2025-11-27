"""Match CMS 2024-2025 data for District 6 only (faster)."""

import pandas as pd
import numpy as np
import re
from pathlib import Path


def clean_jcrl(jcrl_value):
    """Extract base route code from JCRL field."""
    if pd.isna(jcrl_value):
        return None
    s = str(jcrl_value).strip()
    base = re.sub(r'\s*\d+\s*$', '', s)
    return base.strip()


def extract_route_from_code(code_str):
    """Extract (route_type, route_nbr) from JCRL or NLFID."""
    if pd.isna(code_str):
        return None, None
    m = re.search(r'([A-Z]{2})(\d{5})', str(code_str))
    if m:
        return m.group(1), int(m.group(2))
    return None, None


print("Loading data files...")
df_2024_full = pd.read_csv("backend/data/24CarGrowthData(CMS5).csv", low_memory=False)
df_2025_full = pd.read_csv("backend/data/CMS_2025.csv", low_memory=False)

# Filter to District 6 only (Columbus)
print("Filtering to District 6...")
if 'DISTRICT' in df_2024_full.columns:
    df_2024 = df_2024_full[df_2024_full['DISTRICT'] == 6].copy()
else:
    print("Warning: DISTRICT column not found in 2024 data")
    df_2024 = df_2024_full.copy()

if 'ODOT_DISTRICT' in df_2025_full.columns:
    df_2025 = df_2025_full[df_2025_full['ODOT_DISTRICT'] == 6].copy()
else:
    print("Warning: ODOT_DISTRICT column not found in 2025 data")
    df_2025 = df_2025_full.copy()

print(f"District 6 - 2024 rows: {len(df_2024)}")
print(f"District 6 - 2025 rows: {len(df_2025)}")

# Prepare 2024 data
print("\nPreparing 2024 data...")
df_2024['jcrl_base'] = df_2024['JCRL'].apply(clean_jcrl)
df_2024['route_info'] = df_2024['jcrl_base'].apply(extract_route_from_code)
df_2024['rtype'] = df_2024['route_info'].apply(lambda x: x[0])
df_2024['rnbr'] = df_2024['route_info'].apply(lambda x: x[1])

# Use TRUELOG or A for position
position_col = 'TRUELOG' if 'TRUELOG' in df_2024.columns else 'A'
df_2024['pos'] = pd.to_numeric(df_2024[position_col], errors='coerce')

# Normalize position within each route
df_2024['pos_norm'] = df_2024.groupby(['rtype', 'rnbr'])['pos'].transform(
    lambda x: (x - x.min()) / (x.max() - x.min()) if (x.max() > x.min()) else 0
)

# Prepare 2025 data
print("Preparing 2025 data...")
df_2025['pos'] = pd.to_numeric(df_2025['STL_BEGIN_NBR'], errors='coerce')
df_2025['pos_norm'] = df_2025.groupby(['ROUTE_TYPE', 'ROUTE_NBR'])['pos'].transform(
    lambda x: (x - x.min()) / (x.max() - x.min()) if (x.max() > x.min()) else 0
)

# Matching
print("\nMatching rows...")
matches = []
tolerance = 0.1  # Allow 10% normalized position difference

for idx24, row24 in df_2024.iterrows():
    if pd.isna(row24['rtype']) or pd.isna(row24['rnbr']):
        continue
    
    # Find 2025 candidates with same route
    mask = (
        (df_2025['ROUTE_TYPE'] == row24['rtype']) &
        (df_2025['ROUTE_NBR'] == row24['rnbr'])
    )
    candidates = df_2025[mask].copy()
    
    if candidates.empty:
        continue
    
    # Find closest position
    candidates['pos_diff'] = (candidates['pos_norm'] - row24['pos_norm']).abs()
    best_idx = candidates['pos_diff'].idxmin()
    best_diff = candidates.loc[best_idx, 'pos_diff']
    
    if best_diff <= tolerance:
        matches.append({
            'idx_2024': idx24,
            'idx_2025': best_idx,
            'route_type': row24['rtype'],
            'route_nbr': row24['rnbr'],
            'pos_diff': best_diff,
        })

print(f"✓ Matched {len(matches)} rows (out of {len(df_2024)} in 2024)")
print(f"  Match rate: {len(matches) / len(df_2024) * 100:.1f}%")

# Create merged dataset
print("\nCreating merged dataset...")
merged = df_2025.copy()
merged['car_growth_2024'] = np.nan
merged['truck_growth_2024'] = np.nan

for match in matches:
    idx25 = match['idx_2025']
    idx24 = match['idx_2024']
    
    if 'CARGROWRATE' in df_2024.columns:
        merged.loc[idx25, 'car_growth_2024'] = df_2024.loc[idx24, 'CARGROWRATE']
    if 'TRKGROWRATE' in df_2024.columns:
        merged.loc[idx25, 'truck_growth_2024'] = df_2024.loc[idx24, 'TRKGROWRATE']

# Save
output_file = Path("backend/data/CMS_D6_2024_2025_merged.csv")
merged.to_csv(output_file, index=False)
print(f"\n✓ Saved: {output_file}")
print(f"  Total rows: {len(merged)}")
print(f"  Rows with 2024 car growth: {merged['car_growth_2024'].notna().sum()}")
print(f"  Rows with 2025 car growth: {merged['CAR_GROWTH_NBR'].notna().sum()}")

# Show sample
print("\n=== Sample Matched Data ===")
sample = merged[merged['car_growth_2024'].notna()].head(5)
cols = ['NLFID', 'ROUTE_TYPE', 'ROUTE_NBR', 'car_growth_2024', 'CAR_GROWTH_NBR']
print(sample[cols].to_string(index=False))
