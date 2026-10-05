"""
Integrate Census LODES employment data at county level with traffic data.

This script aggregates employment data to Franklin County level to capture
temporal employment trends, similar to the demographic data approach.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from backend.core.preprocessing import load_all_data


def load_county_employment() -> Optional[pd.DataFrame]:
    """
    Load LODES employment data and aggregate to Franklin County by year.
    
    Returns:
        DataFrame with columns: year, total_jobs, job_growth_rate,
                               high_wage_share, job_change_absolute
        Returns None if no files found.
    """
    employment_dir = Path("backend/employment")
    
    print("=" * 80)
    print("LOADING LODES EMPLOYMENT DATA")
    print("=" * 80)
    
    # Map years to expected filenames
    lodes_files = {
        2019: employment_dir / "oh_wac_S000_JT00_2019.csv",
        2020: employment_dir / "oh_wac_S000_JT00_2020.csv",
        2021: employment_dir / "oh_wac_S000_JT00_2021.csv",
        2022: employment_dir / "oh_wac_S000_JT00_2022.csv",
    }
    
    # Load and aggregate each year
    yearly_data = []
    
    for year, filepath in lodes_files.items():
        if not filepath.exists():
            print(f"Warning: Missing {year}: {filepath.name}")
            continue
            
        print(f"\nProcessing {year}...")
        
        # Load file
        df = pd.read_csv(filepath)
        print(f"  Loaded {len(df):,} census blocks (all Ohio)")
        
        # Filter to Franklin County (FIPS code starts with 39049)
        # w_geocode is 15-digit: 2-digit state + 3-digit county + 6-digit tract + 4-digit block
        df['fips_prefix'] = df['w_geocode'].astype(str).str[:5]
        df_franklin = df[df['fips_prefix'] == '39049'].copy()
        print(f"  Filtered to {len(df_franklin):,} Franklin County blocks")
        
        # Aggregate to county level
        total_jobs = df_franklin['C000'].sum()
        high_wage_jobs = df_franklin['CE03'].sum()  # Jobs earning >$3,333/month
        high_wage_share = high_wage_jobs / total_jobs if total_jobs > 0 else 0
        
        yearly_data.append({
            'year': year,
            'total_jobs': total_jobs,
            'high_wage_jobs': high_wage_jobs,
            'high_wage_share': high_wage_share
        })
        
        print(f"  Total Franklin County jobs: {total_jobs:,}")
        print(f"  High-wage jobs (>$3,333/month): {high_wage_jobs:,} ({high_wage_share:.1%})")
    
    if not yearly_data:
        print("\nError: No employment data loaded")
        return None
    
    # Create DataFrame
    df_employment = pd.DataFrame(yearly_data)
    
    # Calculate derived features
    df_employment['job_growth_rate'] = df_employment['total_jobs'].pct_change() * 100
    df_employment['job_growth_from_2019'] = (
        (df_employment['total_jobs'] / df_employment['total_jobs'].iloc[0] - 1) * 100
    )
    df_employment['job_change_absolute'] = df_employment['total_jobs'].diff()
    
    print("\n" + "=" * 80)
    print("FRANKLIN COUNTY EMPLOYMENT SUMMARY")
    print("=" * 80)
    print(df_employment.to_string(index=False))
    
    return df_employment


def integrate_employment_with_traffic(df_employment: pd.DataFrame) -> None:
    """
    Merge county-level employment data with traffic data.
    
    Args:
        df_employment: DataFrame with employment metrics by year
    """
    print("\n" + "=" * 80)
    print("LOADING TRAFFIC DATA")
    print("=" * 80)
    
    # Load traffic data
    df_traffic = load_all_data("backend/data")
    print(f"Loaded {len(df_traffic):,} traffic records")
    print(f"Years: {sorted(df_traffic['year'].unique())}")
    
    print("\n" + "=" * 80)
    print("MERGING EMPLOYMENT WITH TRAFFIC")
    print("=" * 80)
    
    # Merge on year
    df_merged = df_traffic.merge(df_employment, on='year', how='left')
    
    # Carry forward 2022 values to 2023 and 2024
    print("\nCarrying forward 2022 employment data to 2023-2024...")
    employment_cols = ['total_jobs', 'high_wage_jobs', 'high_wage_share',
                      'job_growth_rate', 'job_growth_from_2019', 'job_change_absolute']
    
    for col in employment_cols:
        # Get 2022 value
        value_2022 = df_merged[df_merged['year'] == 2022][col].iloc[0] if len(df_merged[df_merged['year'] == 2022]) > 0 else None
        if value_2022 is not None:
            df_merged.loc[df_merged['year'].isin([2023, 2024]), col] = value_2022
    
    # Check merge results
    segments_with_data = df_merged[employment_cols[0]].notna().sum()
    match_rate = segments_with_data / len(df_merged) * 100
    print(f"Segments with employment data: {segments_with_data:,} ({match_rate:.1f}%)")
    
    # Save merged data
    output_path = Path("backend/data/processed/traffic_with_employment.csv")
    output_path.parent.mkdir(exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path}")
    
    # Summary statistics by year
    print("\n" + "=" * 80)
    print("EMPLOYMENT METRICS BY YEAR")
    print("=" * 80)
    
    summary = df_merged.groupby('year').agg({
        'total_jobs': ['first', 'mean'],  # All segments have same value
        'job_growth_rate': 'first',
        'job_growth_from_2019': 'first',
        'high_wage_share': 'first'
    }).round(2)
    print(summary)
    
    # Calculate correlations with target if it exists
    if 'car_growth_nbr' in df_merged.columns:
        print("\n" + "=" * 80)
        print("CORRELATION WITH CAR GROWTH")
        print("=" * 80)
        
        for col in employment_cols:
            if col in df_merged.columns:
                corr = df_merged[col].corr(df_merged['car_growth_nbr'])
                sign = "+" if corr >= 0 else ""
                print(f"  {col:30s} {sign}{corr:.3f}")


def main():
    """Main execution function."""
    print("=" * 80)
    print(" " * 20 + "COUNTY-LEVEL EMPLOYMENT INTEGRATION")
    print("=" * 80)
    
    # Load and aggregate employment data
    df_employment = load_county_employment()
    if df_employment is None:
        return
    
    # Integrate with traffic data
    integrate_employment_with_traffic(df_employment)
    
    print("\n" + "=" * 80)
    print("INTEGRATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Update backend/train_model.py to include employment features:")
    print("   - total_jobs")
    print("   - job_growth_rate")
    print("   - job_growth_from_2019")
    print("   - high_wage_share")
    print("\n2. Retrain model:")
    print("   python backend/train_model.py")
    print("\n3. Evaluate R-squared improvement vs baseline (0.304)")


if __name__ == "__main__":
    main()
