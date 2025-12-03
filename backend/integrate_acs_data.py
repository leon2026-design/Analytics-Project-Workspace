"""
Integrate ACS Demographic and Housing data with traffic predictions.

Handles missing 2020 data (pandemic census disruption) by interpolating values.
Extracts key demographic indicators that influence traffic growth.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re


def clean_numeric_value(value):
    """Convert ACS string values to numeric, handling special characters."""
    if pd.isna(value) or value in ['N', '(X)', '*****', '-']:
        return np.nan
    
    # Remove commas and convert to float
    try:
        return float(str(value).replace(',', '').replace('%', ''))
    except (ValueError, AttributeError):
        return np.nan


def load_acs_file(filepath, year):
    """Load and parse a single ACS demographic file."""
    if not Path(filepath).exists():
        print(f"⚠️  Missing: {filepath}")
        return None
    
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Extract Franklin County Estimate column (column index 1)
    county_col = [col for col in df.columns if 'Franklin County' in col and 'Estimate' in col][0]
    
    # Extract key metrics by matching row labels
    metrics = {
        'year': year,
        'total_population': None,
        'median_age': None,
        'total_housing_units': None,
        'under_18_years': None,
        'age_18_to_64': None,  # Working age
        'age_65_over': None,
    }
    
    for idx, row in df.iterrows():
        label = row['Label (Grouping)'].strip()
        value = row[county_col]
        
        # Total population (first occurrence)
        if 'Total population' in label and metrics['total_population'] is None:
            metrics['total_population'] = clean_numeric_value(value)
        
        # Median age
        elif 'Median age (years)' in label:
            metrics['median_age'] = clean_numeric_value(value)
        
        # Total housing units
        elif label == 'Total housing units':
            metrics['total_housing_units'] = clean_numeric_value(value)
        
        # Age breakdowns
        elif label == '        Under 18 years':
            metrics['under_18_years'] = clean_numeric_value(value)
        elif label == '        65 years and over':
            metrics['age_65_over'] = clean_numeric_value(value)
    
    # Calculate working-age population (18-64)
    if all(v is not None for v in [metrics['total_population'], 
                                     metrics['under_18_years'], 
                                     metrics['age_65_over']]):
        metrics['age_18_to_64'] = (
            metrics['total_population'] 
            - metrics['under_18_years'] 
            - metrics['age_65_over']
        )
    
    return metrics


def load_all_acs_demographics():
    """Load ACS data for all available years (2019, 2021-2023; 2020 missing)."""
    
    data_dir = Path("backend/data")
    
    # Map years to files (2020 is missing due to pandemic)
    acs_files = {
        2019: data_dir / "ACSDemographicHousing2019.csv",
        2021: data_dir / "ACSDemographicHousing2021.csv",
        2022: data_dir / "ACSDemographicHousing2022.csv",
        2023: data_dir / "ACSDemographicHousing2023.csv",
    }
    
    demographics = []
    
    for year, filepath in acs_files.items():
        print(f"Loading {year} ACS data...")
        metrics = load_acs_file(filepath, year)
        if metrics:
            demographics.append(metrics)
    
    df = pd.DataFrame(demographics)
    
    # Interpolate missing 2020 data
    print("\n⚠️  2020 data missing (pandemic), interpolating from 2019 and 2021...")
    df = df.set_index('year').sort_index()
    df = df.reindex(range(2019, 2024))  # Add 2020 row
    df = df.interpolate(method='linear')  # Linear interpolation
    df = df.reset_index()
    df = df.rename(columns={'index': 'year'})
    df['year'] = df['year'].astype(int)
    
    # Calculate derived features
    df['population_growth_rate'] = df['total_population'].pct_change() * 100  # Percentage
    df['working_age_ratio'] = df['age_18_to_64'] / df['total_population'] * 100
    df['elderly_ratio'] = df['age_65_over'] / df['total_population'] * 100
    
    # Cumulative population growth since 2019
    baseline_pop = df.loc[df['year'] == 2019, 'total_population'].values[0]
    df['cumulative_population_growth'] = (
        (df['total_population'] - baseline_pop) / baseline_pop * 100
    )
    
    print("\n✓ ACS Demographics Loaded:")
    print(df.to_string(index=False))
    print(f"\n📊 Summary:")
    print(f"   • 2019-2023 population growth: {df['cumulative_population_growth'].iloc[-1]:.2f}%")
    print(f"   • Average annual growth rate: {df['population_growth_rate'].mean():.2f}%")
    print(f"   • 2020 data interpolated from surrounding years")
    
    return df


def integrate_demographics_into_traffic():
    """Merge ACS demographics with traffic data and save enriched dataset."""
    from backend.preprocessing import load_all_data
    
    print("\n" + "="*70)
    print("INTEGRATING ACS DEMOGRAPHICS WITH TRAFFIC DATA")
    print("="*70 + "\n")
    
    # Load demographics
    df_demo = load_all_acs_demographics()
    
    # Load traffic data
    print("\nLoading traffic data...")
    df_traffic = load_all_data("backend/data", use_merged_2024_2025=True)
    
    print(f"Traffic data shape: {df_traffic.shape}")
    print(f"Years in traffic data: {sorted(df_traffic['year'].unique())}")
    
    # Merge on year
    print("\nMerging demographics with traffic data...")
    df_merged = df_traffic.merge(df_demo, on='year', how='left')
    
    # Check for missing values
    demo_cols = [
        'total_population', 'median_age', 'total_housing_units',
        'population_growth_rate', 'working_age_ratio', 'cumulative_population_growth'
    ]
    missing_count = df_merged[demo_cols].isna().sum().sum()
    
    print(f"\n✓ Merged dataset: {len(df_merged):,} rows")
    print(f"✓ New demographic features: {len(demo_cols)}")
    print(f"✓ Missing values in demographic columns: {missing_count}")
    
    if missing_count > 0:
        print("\n⚠️  Warning: Some rows have missing demographic data")
        print("   This is expected for years outside 2019-2023 range")
    
    # Save enriched dataset
    output_path = Path("backend/data/processed/traffic_with_demographics.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    print(f"\n✓ Saved enriched dataset: {output_path}")
    
    # Save demographics summary separately
    demo_summary_path = Path("backend/data/processed/acs_demographics_summary.csv")
    df_demo.to_csv(demo_summary_path, index=False)
    print(f"✓ Saved demographics summary: {demo_summary_path}")
    
    return df_merged, df_demo


def preview_feature_impact():
    """Preview how demographic features correlate with car growth."""
    from backend.preprocessing import load_all_data
    
    print("\n" + "="*70)
    print("DEMOGRAPHIC FEATURE PREVIEW")
    print("="*70 + "\n")
    
    # Load merged data
    df_demo = load_all_acs_demographics()
    df_traffic = load_all_data("backend/data", use_merged_2024_2025=True)
    df_merged = df_traffic.merge(df_demo, on='year', how='left')
    
    # Calculate correlations with car_growth_nbr
    if 'car_growth_nbr' in df_merged.columns:
        demo_cols = [
            'total_population', 'population_growth_rate', 'median_age',
            'working_age_ratio', 'cumulative_population_growth'
        ]
        
        correlations = df_merged[demo_cols + ['car_growth_nbr']].corr()['car_growth_nbr'].drop('car_growth_nbr')
        correlations = correlations.sort_values(ascending=False)
        
        print("Correlation with car_growth_nbr:")
        for feature, corr in correlations.items():
            if pd.notna(corr):
                bar = '█' * int(abs(corr) * 50)
                sign = '+' if corr > 0 else '-'
                print(f"  {feature:35s} {sign} {bar} {corr:+.3f}")
            else:
                print(f"  {feature:35s}   (insufficient data)")
    
    # Year-by-year summary
    print("\n\nYear-by-Year Summary:")
    print("-" * 70)
    yearly = df_merged.groupby('year').agg({
        'total_population': 'first',
        'population_growth_rate': 'first',
        'car_growth_nbr': 'mean'
    }).reset_index()
    
    yearly.columns = ['Year', 'Population', 'Pop Growth %', 'Avg Car Growth %']
    print(yearly.to_string(index=False))


if __name__ == "__main__":
    # Run full integration
    df_merged, df_demo = integrate_demographics_into_traffic()
    
    # Preview correlations
    preview_feature_impact()
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Update backend/train_model.py to include new features:")
    print("   • total_population")
    print("   • population_growth_rate")
    print("   • median_age")
    print("   • working_age_ratio")
    print("   • cumulative_population_growth")
    print("\n2. Retrain model:")
    print("   python backend/train_model.py")
    print("\n3. Compare R² before/after demographic features")
    print("="*70 + "\n")
