"""Match and merge CMS5 2024 data with CMS 2025 data.

This script handles the format differences between:
- 2024: 24CarGrowthData(CMS5).csv with JCRL field containing embedded mileposts
- 2025: CMS_2025.csv with separate NLFID and station fields

Key matching strategy:
1. Extract base route code from JCRL (strip trailing numbers/spaces)
2. Match on base route + station/milepost proximity
3. Merge growth data from 2024 into 2025 structure
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path


def clean_jcrl(jcrl_value):
    """Extract base route code from JCRL field.
    
    Example:
        'SADASR00032**C    0 ' -> 'SADASR00032**C'
        'SADASR00032**C  334 ' -> 'SADASR00032**C'
    """
    if pd.isna(jcrl_value):
        return None
    
    # Convert to string and strip
    s = str(jcrl_value).strip()
    
    #Remove trailing digits and spaces
    #Pattern: keep everything until we hit trailing numbers/spaces
    #Most JCRL codes end with **C or similar, then have trailing milepost
    base = re.sub(r'\s*\d+\s*$', '', s)
    
    return base.strip()


def extract_route_info(jcrl_base):
    """Extract route type and number from JCRL base code.
    
    Example:
        'SADASR00032**C' -> ('SR', 32)
        'SWOOUS00006**C' -> ('US', 6)
        'SWOOIR00070**C' -> ('IR', 70)
    """
    if pd.isna(jcrl_base):
        return None, None
    
    #Pattern: letters followed by 5 digits
    #Common prefixes: SR, US, IR, CR
    m = re.search(r'([A-Z]{2})(\d{5})', jcrl_base)
    if m:
        route_type = m.group(1)
        route_nbr = int(m.group(2))
        return route_type, route_nbr
    
    return None, None


def normalize_position(df, position_col, group_col):
    """Normalize position within each route to 0-1 range."""
    return df.groupby(group_col)[position_col].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) if (x.max() > x.min()) else 0
    )


def match_cms_2024_to_2025(df_2024, df_2025, tolerance=0.05):
    """Match 2024 CMS5 rows to 2025 CMS rows.
    
    Args:
        df_2024: DataFrame from 24CarGrowthData(CMS5).csv
        df_2025: DataFrame from CMS_2025.csv
        tolerance: Maximum normalized position difference for matching
        
    Returns:
        DataFrame with matched 2024 data merged into 2025 structure
    """
    print("Starting CMS 2024-2025 matching process...")
    print(f"2024 rows: {len(df_2024)}")
    print(f"2025 rows: {len(df_2025)}")
    
    # Step 1: Clean and prepare 2024 data
    df24 = df_2024.copy()
    df24['jcrl_base'] = df24['JCRL'].apply(clean_jcrl)
    df24['route_type_24'], df24['route_nbr_24'] = zip(*df24['jcrl_base'].apply(extract_route_info))
    
    # Use TRUELOG for position (or A if TRUELOG not available)
    position_col = 'TRUELOG' if 'TRUELOG' in df24.columns else 'A'
    df24['position_24'] = pd.to_numeric(df24[position_col], errors='coerce')
    
    # Normalize position within each route
    df24['norm_pos_24'] = normalize_position(df24, 'position_24', 'jcrl_base')
    
    print(f"\n2024 unique routes: {df24['jcrl_base'].nunique()}")
    print(f"2024 rows with valid position: {df24['position_24'].notna().sum()}")
    
    # Step 2: Prepare 2025 data
    df25 = df_2025.copy()
    
    # Use STL_BEGIN_NBR as primary position, or midpoint of begin/end
    if 'STL_BEGIN_NBR' in df25.columns and 'STL_END_NBR' in df25.columns:
        df25['position_25'] = pd.to_numeric(df25['STL_BEGIN_NBR'], errors='coerce')
    elif 'CTL_BEGIN_NBR' in df25.columns:
        df25['position_25'] = pd.to_numeric(df25['CTL_BEGIN_NBR'], errors='coerce')
    else:
        print("Warning: No position columns found in 2025 data")
        df25['position_25'] = 0
    
    # Normalize position within each route
    if 'ROUTE_NBR' in df25.columns:
        df25['norm_pos_25'] = normalize_position(df25, 'position_25', 'ROUTE_NBR')
    else:
        df25['norm_pos_25'] = 0
    
    print(f"\n2025 unique routes: {df25['ROUTE_NBR'].nunique() if 'ROUTE_NBR' in df25.columns else 'N/A'}")
    print(f"2025 rows with valid position: {df25['position_25'].notna().sum()}")
    
    # Step 3: Match rows
    matches = []
    unmatched_2024 = []
    
    for idx24, row24 in df24.iterrows():
        if pd.isna(row24['route_type_24']) or pd.isna(row24['route_nbr_24']):
            unmatched_2024.append(idx24)
            continue
        
        # Filter 2025 candidates by route
        mask = (
            (df25['ROUTE_TYPE'].astype(str).str.upper() == row24['route_type_24']) &
            (df25['ROUTE_NBR'] == row24['route_nbr_24'])
        )
        candidates = df25[mask]
        
        if candidates.empty:
            unmatched_2024.append(idx24)
            continue
        
        # Find closest position match
        candidates = candidates.copy()
        candidates['pos_diff'] = (candidates['norm_pos_25'] - row24['norm_pos_24']).abs()
        
        best_match = candidates.loc[candidates['pos_diff'].idxmin()]
        
        if best_match['pos_diff'] <= tolerance:
            matches.append({
                'idx_2024': idx24,
                'idx_2025': best_match.name,
                'jcrl_base': row24['jcrl_base'],
                'route_type': row24['route_type_24'],
                'route_nbr': row24['route_nbr_24'],
                'pos_diff': best_match['pos_diff'],
                'position_24': row24['position_24'],
                'position_25': best_match['position_25'],
            })
        else:
            unmatched_2024.append(idx24)
    
    print(f"\n--- Matching Results ---")
    print(f"Matched: {len(matches)}")
    print(f"Unmatched 2024 rows: {len(unmatched_2024)}")
    print(f"Match rate: {len(matches) / len(df24) * 100:.1f}%")
    
    if matches:
        match_df = pd.DataFrame(matches)
        print(f"\nPosition difference stats:")
        print(match_df['pos_diff'].describe())
    
    #Step 4: Create merged dataset
    #Start with 2025 structure
    merged = df25.copy()
    
    #Add 2024 growth data where matched
    merged['car_growth_2024'] = np.nan
    merged['truck_growth_2024'] = np.nan
    
    for match in matches:
        idx25 = match['idx_2025']
        idx24 = match['idx_2024']
        
        # Copy growth rates from 2024
        if 'CARGROWRATE' in df24.columns:
            merged.loc[idx25, 'car_growth_2024'] = df24.loc[idx24, 'CARGROWRATE']
        if 'TRKGROWRATE' in df24.columns:
            merged.loc[idx25, 'truck_growth_2024'] = df24.loc[idx24, 'TRKGROWRATE']
    
    print(f"\n2025 rows with 2024 growth data: {merged['car_growth_2024'].notna().sum()}")
    
    return merged, match_df if matches else None, unmatched_2024


def main():
    #Paths
    data_dir = Path("backend/data")
    file_2024 = data_dir / "24CarGrowthData(CMS5).csv"
    file_2025 = data_dir / "CMS_2025.csv"
    output_file = data_dir / "CMS_2024_2025_merged.csv"
    
    #Load data
    print("Loading data files...")
    df_2024 = pd.read_csv(file_2024, low_memory=False)
    df_2025 = pd.read_csv(file_2025, low_memory=False)
    
    print(f"\n2024 columns: {list(df_2024.columns[:10])}...")
    print(f"2025 columns: {list(df_2025.columns[:10])}...")
    
    #Perform matching
    merged, match_details, unmatched = match_cms_2024_to_2025(df_2024, df_2025)
    
    #Save results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_file, index=False)
    print(f"\n✓ Merged data saved to: {output_file}")
    
    if match_details is not None:
        match_file = data_dir / "match_details.csv"
        match_details.to_csv(match_file, index=False)
        print(f"✓ Match details saved to: {match_file}")
    
    #Summary statistics
    print("\n=== Summary ===")
    print(f"Total 2025 rows: {len(merged)}")
    print(f"Rows with 2024 car growth: {merged['car_growth_2024'].notna().sum()}")
    print(f"Rows with 2025 car growth: {merged['CAR_GROWTH_NBR'].notna().sum() if 'CAR_GROWTH_NBR' in merged.columns else 0}")
    
    #Show sample matches
    print("\n=== Sample Matched Rows ===")
    sample = merged[merged['car_growth_2024'].notna()].head(5)
    cols_to_show = ['NLFID', 'ROUTE_TYPE', 'ROUTE_NBR', 'position_25', 'car_growth_2024', 'CAR_GROWTH_NBR']
    cols_to_show = [c for c in cols_to_show if c in merged.columns]
    print(sample[cols_to_show].to_string(index=False))


if __name__ == "__main__":
    main()
