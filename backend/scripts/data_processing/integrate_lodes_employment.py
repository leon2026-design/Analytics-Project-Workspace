"""
Integrate Census LODES employment data into traffic dataset.

This script:
1. Loads LODES Workplace Area Characteristics (WAC) files for Ohio
2. Filters to Franklin County census blocks
3. Aggregates to census tract level
4. Calculates employment features (growth rates, wage distribution, etc.)
5. Matches road segments to census tracts
6. Merges with traffic data
"""

import pandas as pd
import numpy as np
from pathlib import Path

from backend.core.preprocessing import load_all_data


def load_lodes_files():
    """Load and process LODES Workplace Area Characteristics (WAC) files."""
    
    employment_dir = Path("backend/employment")
    
    print("="*70)
    print("LOADING LODES EMPLOYMENT DATA")
    print("="*70)
    
    # Map years to expected filenames
    lodes_files = {
        2019: employment_dir / "oh_wac_S000_JT00_2019.csv",
        2020: employment_dir / "oh_wac_S000_JT00_2020.csv",
        2021: employment_dir / "oh_wac_S000_JT00_2021.csv",
        2022: employment_dir / "oh_wac_S000_JT00_2022.csv",
    }
    
    # Check which files exist
    missing_files = []
    for year, filepath in lodes_files.items():
        if not filepath.exists():
            missing_files.append(f"{year}: {filepath.name}")
    
    if missing_files:
        print("\nWarning: Missing LODES files:")
        for msg in missing_files:
            print(f"  - {msg}")
        if len(missing_files) == len(lodes_files):
            print("\nError: No LODES files found. Exiting.")
            return pd.DataFrame()
    
    all_data = []
    
    for year, filepath in lodes_files.items():
        if not filepath.exists():
            continue
        
        print(f"\nLoading {year}: {filepath.name}")
        
        try:
            # Load LODES file with w_geocode as string to preserve leading zeros
            df = pd.read_csv(filepath, dtype={'w_geocode': str}, low_memory=False)
            print(f"  Loaded {len(df):,} census blocks (all Ohio)")
            
            # Ensure w_geocode is 15 digits (pad with zeros if needed)
            df['w_geocode'] = df['w_geocode'].str.zfill(15)
            
            # Filter to Franklin County (FIPS code: 39049)
            # w_geocode format: SSCCCTTTTTTBBBB
            # SS = State (39 = Ohio), CCC = County (049 = Franklin)
            df_franklin = df[df['w_geocode'].str.startswith('39049')].copy()
            print(f"  Filtered to {len(df_franklin):,} Franklin County blocks")
            
            # Extract census tract (first 11 digits: state + county + tract)
            df_franklin['tract'] = df_franklin['w_geocode'].str[:11]
            
            # Aggregate census blocks to tracts
            # Column descriptions:
            # C000 = Total jobs (all types)
            # CE01 = Jobs with earnings $1,250/month or less
            # CE02 = Jobs with earnings $1,251-$3,333/month  
            # CE03 = Jobs with earnings greater than $3,333/month
            agg_columns = {}
            if 'C000' in df_franklin.columns:
                agg_columns['C000'] = 'sum'
            if 'CE01' in df_franklin.columns:
                agg_columns['CE01'] = 'sum'
            if 'CE02' in df_franklin.columns:
                agg_columns['CE02'] = 'sum'
            if 'CE03' in df_franklin.columns:
                agg_columns['CE03'] = 'sum'
            
            if not agg_columns:
                print(f"  Error: No expected columns (C000, CE01, CE02, CE03) found")
                continue
            
            df_tract = df_franklin.groupby('tract').agg(agg_columns).reset_index()
            
            # Rename columns for clarity
            column_mapping = {
                'C000': 'total_jobs',
                'CE01': 'jobs_low_wage',
                'CE02': 'jobs_mid_wage',
                'CE03': 'jobs_high_wage'
            }
            df_tract.rename(columns=column_mapping, inplace=True)
            df_tract['year'] = year
            
            print(f"  Aggregated to {len(df_tract)} census tracts")
            print(f"  Total Franklin County jobs: {df_tract['total_jobs'].sum():,}")
            
            all_data.append(df_tract)
            
        except Exception as e:
            print(f"  Error processing {filepath.name}: {e}")
            continue
    
    if not all_data:
        print("\nError: No LODES data loaded successfully")
        return pd.DataFrame()
    
    # Combine all years
    df_combined = pd.concat(all_data, ignore_index=True)
    df_combined = df_combined.sort_values(['tract', 'year']).reset_index(drop=True)
    
    print("\n" + "="*70)
    print("EMPLOYMENT DATA SUMMARY")
    print("="*70)
    print(f"Total records: {len(df_combined):,}")
    print(f"Unique census tracts: {df_combined['tract'].nunique()}")
    print(f"Years: {sorted(df_combined['year'].unique())}")
    
    print("\nJobs by year:")
    year_summary = df_combined.groupby('year')['total_jobs'].agg(['sum', 'mean', 'median', 'std'])
    year_summary.columns = ['Total', 'Mean', 'Median', 'Std Dev']
    print(year_summary.round(0).to_string())
    
    return df_combined


def calculate_employment_features(df):
    """Calculate derived employment features from raw job counts."""
    
    print("\n" + "="*70)
    print("CALCULATING EMPLOYMENT FEATURES")
    print("="*70)
    
    # Sort by tract and year for proper time series calculations
    df = df.sort_values(['tract', 'year']).copy()
    
    # 1. Year-over-year job growth rate (percentage change)
    df['job_growth_rate'] = df.groupby('tract')['total_jobs'].pct_change()
    print("Created: job_growth_rate (year-over-year % change)")
    
    # 2. Cumulative growth from 2019 baseline
    def calculate_cumulative_growth(group):
        if len(group) == 0 or group.iloc[0] == 0:
            return pd.Series([0] * len(group), index=group.index)
        baseline = group.iloc[0]
        return (group - baseline) / baseline
    
    df['job_growth_from_2019'] = df.groupby('tract')['total_jobs'].transform(calculate_cumulative_growth)
    print("Created: job_growth_from_2019 (cumulative % change from 2019)")
    
    # 3. High-wage job share (if wage columns exist)
    if 'jobs_high_wage' in df.columns and 'total_jobs' in df.columns:
        df['high_wage_share'] = df['jobs_high_wage'] / df['total_jobs'].replace(0, np.nan)
        df['high_wage_share'] = df['high_wage_share'].fillna(0)
        print("Created: high_wage_share (% of jobs earning >$3,333/month)")
    else:
        df['high_wage_share'] = 0
        print("Skipped: high_wage_share (wage columns not available)")
    
    # 4. Employment density quartiles (relative ranking by year)
    for year in df['year'].unique():
        mask = df['year'] == year
        try:
            df.loc[mask, 'job_density_quartile'] = pd.qcut(
                df.loc[mask, 'total_jobs'], 
                q=4, 
                labels=[1, 2, 3, 4],
                duplicates='drop'
            )
        except ValueError:
            # If qcut fails (e.g., too many duplicate values), use regular cut
            df.loc[mask, 'job_density_quartile'] = pd.cut(
                df.loc[mask, 'total_jobs'],
                bins=4,
                labels=[1, 2, 3, 4]
            )
    print("Created: job_density_quartile (1=Low, 2=Medium, 3=High, 4=Very High)")
    
    # 5. High-employment area flag (top 25% of tracts by year)
    df['high_employment_area'] = 0
    for year in df['year'].unique():
        threshold = df[df['year'] == year]['total_jobs'].quantile(0.75)
        mask = (df['year'] == year) & (df['total_jobs'] >= threshold)
        df.loc[mask, 'high_employment_area'] = 1
    print("Created: high_employment_area (binary: 1 = top 25% of tracts)")
    
    # 6. Absolute job change (net jobs added/lost)
    df['job_change_absolute'] = df.groupby('tract')['total_jobs'].diff()
    print("Created: job_change_absolute (net jobs added/lost year-over-year)")
    
    print(f"\nSuccessfully created 6 employment features")
    
    # Handle NaN values in growth rates (first year has no prior year)
    df['job_growth_rate'] = df['job_growth_rate'].fillna(0)
    df['job_change_absolute'] = df['job_change_absolute'].fillna(0)
    
    return df


def create_route_to_tract_mapping():
    """
    Create route to census tract mapping for Franklin County.
    
    This is a comprehensive mapping of major routes through Franklin County.
    For production use, this should be replaced with GIS-based spatial join
    using actual segment coordinates.
    
    Returns:
        dict: Mapping of route numbers to census tract codes
    """
    
    # Major routes and their approximate census tracts
    # Tract codes are 11 digits: 39049 (Franklin County) + 6-digit tract number
    route_mapping = {
        # Interstate highways
        '70': ['39049000100', '39049000200', '39049000300', '39049000400', '39049000500',
               '39049002100', '39049002200', '39049002300', '39049002400', '39049002500'],
        '71': ['39049000600', '39049000700', '39049000800', '39049000900', '39049001000',
               '39049001100', '39049008900', '39049009000', '39049009100', '39049009200'],
        '270': ['39049001200', '39049001300', '39049001400', '39049004500', '39049004600',
                '39049005000', '39049005100', '39049006000', '39049006100', '39049007000',
                '39049007100', '39049007200', '39049008000', '39049008100'],
        
        # US Routes
        '23': ['39049000100', '39049000200', '39049001000', '39049001100', '39049008900',
               '39049009000', '39049009100'],
        '33': ['39049000300', '39049000400', '39049002000', '39049002100', '39049002200',
               '39049002300', '39049002400'],
        '40': ['39049000500', '39049000600', '39049001400', '39049001500', '39049001600',
               '39049002600', '39049002700'],
        '42': ['39049001700', '39049001800', '39049001900', '39049002000', '39049009300'],
        '62': ['39049002300', '39049002400', '39049002500', '39049002600', '39049008800'],
        '36': ['39049003900', '39049004000', '39049004100', '39049004200'],
        
        # State Routes
        '3': ['39049000700', '39049000800', '39049000900', '39049001000', '39049007900',
              '39049008000', '39049008100'],
        '16': ['39049003000', '39049003100', '39049003200', '39049003300', '39049003400',
               '39049003500'],
        '37': ['39049001200', '39049001300', '39049004000', '39049004100', '39049004200'],
        '38': ['39049004200', '39049004300', '39049004400', '39049004500'],
        '104': ['39049004500', '39049004600', '39049004700', '39049004800', '39049007300',
                '39049007400', '39049007500'],
        '161': ['39049005000', '39049005100', '39049005200', '39049005300', '39049005400',
                '39049005500'],
        '315': ['39049001600', '39049001700', '39049005500', '39049005600', '39049005700',
                '39049005800'],
        '317': ['39049005800', '39049005900', '39049006000', '39049006100'],
        '229': ['39049004300', '39049004400', '39049004500'],
        '257': ['39049006100', '39049006200', '39049006300'],
        '665': ['39049006400', '39049006500', '39049006600'],
        '10': ['39049007000', '39049007100', '39049007200'],
        '710': ['39049000100', '39049000200', '39049000300'],
        '256': ['39049007600', '39049007700', '39049007800'],
        '745': ['39049008200', '39049008300', '39049008400'],
        '41': ['39049004000', '39049004100', '39049004200'],
        '47': ['39049008500', '39049008600', '39049008700'],
        '56': ['39049007300', '39049007400', '39049007500'],
        '61': ['39049008900', '39049009000', '39049009100'],
        '95': ['39049007000', '39049007100', '39049007200'],
        '309': ['39049009200', '39049009300', '39049009400'],
        '739': ['39049007000', '39049007100', '39049007200'],
        '762': ['39049002400', '39049002500', '39049002600'],
        
        # Default: Central Columbus tract (downtown, high employment)
        'default': '39049000100'
    }
    
    return route_mapping


def match_segments_to_tracts(df_traffic):
    """
    Assign census tracts to road segments based on route information.
    
    Args:
        df_traffic: DataFrame with traffic data
        
    Returns:
        DataFrame with 'tract' column added
    """
    
    print("\n" + "="*70)
    print("MATCHING ROAD SEGMENTS TO CENSUS TRACTS")
    print("="*70)
    
    route_mapping = create_route_to_tract_mapping()
    
    # Find route column in traffic data
    route_col = None
    for col in ['route_nbr', 'ROUTE_NBR', 'route', 'ROUTE']:
        if col in df_traffic.columns:
            route_col = col
            break
    
    if not route_col:
        print("Warning: No route column found in traffic data")
        print(f"Available columns: {df_traffic.columns.tolist()[:20]}...")
        print("Assigning all segments to default tract (downtown Columbus)")
        df_traffic['tract'] = route_mapping['default']
        return df_traffic
    
    print(f"Using route column: {route_col}")
    
    def assign_tract(row):
        """Assign census tract based on route number."""
        route_raw = row[route_col]
        
        # Handle NaN/None
        if pd.isna(route_raw):
            return route_mapping['default']
        
        # Convert to string and clean
        route = str(route_raw).upper().strip()
        
        # Remove common prefixes
        for prefix in ['I-', 'US-', 'SR-', 'OH-', 'I ', 'US ', 'SR ', 'OH ']:
            route = route.replace(prefix, '')
        
        # Remove decimal points and extract integer part
        if '.' in route:
            route = route.split('.')[0]
        
        # Look up in mapping
        if route in route_mapping:
            tracts = route_mapping[route]
            # If multiple tracts for a route, use first one
            # In production, would use milepost/coordinates to select correct tract
            return tracts[0] if isinstance(tracts, list) else tracts
        else:
            return route_mapping['default']
    
    # Assign tracts to all segments
    df_traffic['tract'] = df_traffic.apply(assign_tract, axis=1)
    
    unique_tracts = df_traffic['tract'].nunique()
    default_count = (df_traffic['tract'] == route_mapping['default']).sum()
    matched_count = len(df_traffic) - default_count
    match_pct = (matched_count / len(df_traffic) * 100) if len(df_traffic) > 0 else 0
    
    print(f"Assigned {unique_tracts} unique census tracts to segments")
    print(f"Matched to specific routes: {matched_count:,} segments ({match_pct:.1f}%)")
    print(f"Assigned to default tract: {default_count:,} segments ({100-match_pct:.1f}%)")
    
    return df_traffic


def integrate_employment_with_traffic():
    """Main integration function to merge employment data with traffic data."""
    
    print("\n" + "="*80)
    print(" "*20 + "LODES EMPLOYMENT INTEGRATION")
    print("="*80 + "\n")
    
    # Step 1: Load and process LODES employment data
    df_employment = load_lodes_files()
    
    if df_employment.empty:
        print("\nError: No employment data loaded. Exiting.")
        return None
    
    # Step 2: Calculate derived employment features
    df_employment = calculate_employment_features(df_employment)
    
    # Save processed employment data for reference
    emp_output = Path("backend/data/processed/employment_by_tract_year.csv")
    emp_output.parent.mkdir(parents=True, exist_ok=True)
    df_employment.to_csv(emp_output, index=False)
    print(f"\nSaved processed employment data: {emp_output}")
    
    # Step 3: Load traffic data
    print("\n" + "="*70)
    print("LOADING TRAFFIC DATA")
    print("="*70)
    df_traffic = load_all_data("backend/data")
    print(f"Loaded {len(df_traffic):,} traffic records")
    print(f"Years in traffic data: {sorted(df_traffic['year'].unique())}")
    
    # Step 4: Match road segments to census tracts
    df_traffic = match_segments_to_tracts(df_traffic)
    
    # Step 5: Merge employment data with traffic data
    print("\n" + "="*70)
    print("MERGING EMPLOYMENT WITH TRAFFIC")
    print("="*70)
    
    # Select key employment columns for merge
    emp_cols = ['tract', 'year', 'total_jobs', 'job_growth_rate', 'job_growth_from_2019',
                'high_wage_share', 'high_employment_area', 'job_change_absolute']
    df_employment_merge = df_employment[emp_cols].copy()
    
    df_merged = df_traffic.merge(
        df_employment_merge,
        on=['tract', 'year'],
        how='left'
    )
    
    # Calculate merge success rate
    matched_count = df_merged['total_jobs'].notna().sum()
    matched_pct = (matched_count / len(df_merged) * 100) if len(df_merged) > 0 else 0
    
    print(f"Merged dataset: {len(df_merged):,} rows")
    print(f"Segments with employment data: {matched_count:,} ({matched_pct:.1f}%)")
    
    # Handle years beyond 2022 (carry forward 2022 values)
    max_employment_year = df_employment['year'].max()
    if df_merged['year'].max() > max_employment_year:
        print(f"\nCarrying forward {max_employment_year} employment data to {df_merged['year'].max()}...")
        
        # Forward fill employment features by tract
        for col in ['total_jobs', 'high_wage_share', 'high_employment_area']:
            if col in df_merged.columns:
                df_merged[col] = df_merged.groupby('tract')[col].fillna(method='ffill')
        
        # Recalculate coverage
        matched_count = df_merged['total_jobs'].notna().sum()
        matched_pct = (matched_count / len(df_merged) * 100) if len(df_merged) > 0 else 0
        print(f"After carry-forward: {matched_count:,} segments with data ({matched_pct:.1f}%)")
    
    # Save merged dataset
    merged_output = Path("backend/data/processed/traffic_with_employment.csv")
    df_merged.to_csv(merged_output, index=False)
    print(f"\nSaved merged dataset: {merged_output}")
    
    # Display summary statistics
    print("\n" + "="*70)
    print("EMPLOYMENT SUMMARY BY YEAR")
    print("="*70)
    
    if 'total_jobs' in df_merged.columns:
        summary = df_merged.groupby('year').agg({
            'total_jobs': ['count', 'mean', 'median', 'std']
        }).round(0)
        summary.columns = ['Count', 'Mean Jobs', 'Median Jobs', 'Std Dev']
        print(summary.to_string())
    
    # Correlation analysis
    print("\n" + "="*70)
    print("CORRELATION WITH CAR GROWTH")
    print("="*70)
    
    emp_features = ['total_jobs', 'job_growth_rate', 'job_growth_from_2019', 
                    'high_wage_share', 'high_employment_area', 'job_change_absolute']
    
    # Find car growth column
    car_growth_col = None
    for col in ['car_growth_nbr', 'predicted_car_growth_nbr', 'CAR_GROWTH_NBR']:
        if col in df_merged.columns:
            car_growth_col = col
            break
    
    if car_growth_col:
        available_features = [f for f in emp_features if f in df_merged.columns]
        if available_features:
            correlations = df_merged[available_features + [car_growth_col]].corr()[car_growth_col]
            correlations = correlations[available_features].sort_values(ascending=False)
            print(f"\nCorrelation with {car_growth_col}:")
            for feat, corr in correlations.items():
                print(f"  {feat:30s} {corr:+.3f}")
        else:
            print("No employment features available for correlation analysis")
    else:
        print("Car growth column not found in merged dataset")
    
    print("\n" + "="*80)
    print("INTEGRATION COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Update backend/train_model.py to include employment features:")
    for feat in ['total_jobs', 'job_growth_rate', 'high_employment_area']:
        print(f"   - {feat}")
    print("\n2. Retrain model:")
    print("   python backend/train_model.py")
    print("\n3. Evaluate R-squared improvement vs baseline (0.304)")
    
    return df_merged


if __name__ == "__main__":
    try:
        integrate_employment_with_traffic()
    except Exception as e:
        print(f"\nError during integration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
