"""
Integrate ACS ZIP-level housing occupancy data with traffic predictions.

This script:
1. Loads occupancy data from b25002.43XXX.csv files
2. Creates a route-based mapping to assign ZIP codes to road segments
3. Merges occupancy metrics with traffic data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re


def load_all_zip_occupancy_files():
    """Load all ZIP-level occupancy files from backend/data/occupancystatus."""
    
    occupancy_dir = Path("backend/data/occupancystatus")
    
    if not occupancy_dir.exists():
        print(f"❌ Directory not found: {occupancy_dir}")
        return pd.DataFrame()
    
    # Find all b25002.*.csv files
    csv_files = list(occupancy_dir.glob("b25002.*.csv"))
    
    if not csv_files:
        print(f"❌ No occupancy files found in {occupancy_dir}")
        return pd.DataFrame()
    
    print(f"Found {len(csv_files)} ZIP code occupancy files")
    
    all_data = []
    
    for filepath in csv_files:
        # Extract ZIP code from filename: b25002.43215.csv -> 43215
        zip_match = re.search(r'b25002\.(\d{5})\.csv', filepath.name)
        
        if not zip_match:
            print(f"⚠️  Could not extract ZIP from {filepath.name}")
            continue
        
        zip_code = zip_match.group(1)
        
        try:
            # Read CSV
            df = pd.read_csv(filepath)
            
            # Extract values from the estimate column
            # Column name pattern: "ZCTA5 43215!!Estimate"
            estimate_col = [col for col in df.columns if 'Estimate' in col and zip_code in col]
            
            if not estimate_col:
                print(f"⚠️  No estimate column found in {filepath.name}")
                continue
            
            estimate_col = estimate_col[0]
            
            # Parse occupancy data
            # Row 0: Total housing units
            # Row 1: Occupied
            # Row 2: Vacant
            
            data = {
                'zip_code': zip_code,
                'total_housing_units': None,
                'occupied_units': None,
                'vacant_units': None
            }
            
            for idx, row in df.iterrows():
                label = str(row['Label (Grouping)']).strip()
                value_str = str(row[estimate_col]).replace(',', '')
                
                try:
                    value = float(value_str)
                except (ValueError, AttributeError):
                    continue
                
                if label == 'Total:':
                    data['total_housing_units'] = value
                elif 'Occupied' in label:
                    data['occupied_units'] = value
                elif 'Vacant' in label:
                    data['vacant_units'] = value
            
            # Calculate occupancy rate
            if data['total_housing_units'] and data['total_housing_units'] > 0:
                data['occupancy_rate'] = data['occupied_units'] / data['total_housing_units']
                data['vacancy_rate'] = data['vacant_units'] / data['total_housing_units']
            
            all_data.append(data)
            
        except Exception as e:
            print(f"❌ Error processing {filepath.name}: {e}")
            continue
    
    if not all_data:
        print("❌ No occupancy data loaded")
        return pd.DataFrame()
    
    df_occupancy = pd.DataFrame(all_data)
    
    print(f"\n✓ Loaded occupancy data for {len(df_occupancy)} ZIP codes")
    print(f"  Average occupancy rate: {df_occupancy['occupancy_rate'].mean():.1%}")
    print(f"  Average vacancy rate: {df_occupancy['vacancy_rate'].mean():.1%}")
    
    return df_occupancy


def create_route_to_zip_mapping():
    """
    Create a mapping of routes to their primary ZIP codes.
    
    Based on geographic knowledge of Columbus area routes.
    Expanded to cover all major District 6 routes.
    """
    
    # Comprehensive route mapping for Franklin County (District 6)
    route_zip_map = {
        # === INTERSTATES ===
        ('IR', 70): [43215, 43203, 43213, 43232, 43219, 43068],  # I-70 East-West
        ('IR', 71): [43123, 43207, 43215, 43201, 43214, 43229, 43085],  # I-71 South-North
        ('IR', 270): [43123, 43119, 43228, 43220, 43221, 43017, 43016, 43081, 43082, 43229, 43230, 43232],  # I-270 Outer belt
        
        # === US ROUTES ===
        ('US', 22): [43228, 43223, 43004],  # US-22 Southwest
        ('US', 23): [43123, 43207, 43215, 43201, 43214, 43229, 43085],  # US-23 High Street (N-S corridor)
        ('US', 33): [43110, 43125, 43215, 43219, 43230, 43054],  # US-33 Southeast-Northeast
        ('US', 36): [43119, 43026, 43017],  # US-36 West (Hilliard-Dublin)
        ('US', 40): [43228, 43223, 43213, 43232, 43068],  # US-40 National Road (East-West)
        ('US', 42): [43220, 43212, 43214, 43229, 43082],  # US-42 Northwest
        ('US', 62): [43229, 43214, 43201, 43215],  # US-62 North
        
        # === STATE ROUTES ===
        ('SR', 3): [43085, 43081, 43229, 43219, 43232],  # SR-3 Westerville Rd/Cleveland Ave
        ('SR', 4): [43123, 43207, 43213],  # SR-4 South
        ('SR', 16): [43215, 43203, 43213, 43232, 43068],  # SR-16 Broad Street East
        ('SR', 37): [43016, 43017, 43220, 43212, 43215],  # SR-37 Dublin-Granville Rd
        ('SR', 38): [43026, 43119, 43228, 43223],  # SR-38 West (Hilliard)
        ('SR', 41): [43119, 43026, 43017],  # SR-41 West
        ('SR', 47): [43085, 43082, 43229],  # SR-47 North
        ('SR', 56): [43207, 43110, 43125],  # SR-56 South (Grove City-Groveport)
        ('SR', 61): [43085, 43081, 43082],  # SR-61 North (Delaware County line)
        ('SR', 95): [43204, 43228, 43223],  # SR-95 West Side
        ('SR', 104): [43207, 43223, 43123],  # SR-104 Southwest
        ('SR', 161): [43082, 43081, 43229, 43230, 43054],  # SR-161 Northeast
        ('SR', 229): [43026, 43119, 43228],  # SR-229 Hilliard area
        ('SR', 257): [43016, 43017],  # SR-257 Dublin
        ('SR', 309): [43016, 43082, 43085],  # SR-309 North
        ('SR', 315): [43085, 43229, 43214, 43212, 43220],  # SR-315 North-South
        ('SR', 317): [43220, 43221, 43017, 43016],  # SR-317 Dublin-Upper Arlington
        ('SR', 529): [43119, 43026],  # SR-529 Hilliard-Rome Rd
        ('SR', 665): [43230, 43054],  # SR-665 New Albany
        ('SR', 710): [43123, 43207],  # SR-710 South
        ('SR', 739): [43207, 43204, 43228],  # SR-739 Georgesville Rd
        ('SR', 745): [43110, 43125],  # SR-745 Gender Rd (Southeast)
        ('SR', 762): [43230, 43219],  # SR-762 Hamilton Rd (East)
        
        # === COUNTY ROADS (CR) - General areas ===
        # Most unmapped CRs will fall back to defaults
    }
    
    # Expanded mapping: Add individual routes from map
    expanded_map = {}
    
    for (route_type, route_nbr), zip_list in route_zip_map.items():
        key = (route_type, route_nbr)
        expanded_map[key] = zip_list
    
    # Default ZIP codes for unmapped routes by county
    default_zips = {
        'FRANKLIN': ['43215', '43201', '43219'],  # Downtown, Clintonville, Northeast
        'DELAWARE': ['43015', '43065', '43081'],  # Delaware county (north suburbs)
    }
    
    return expanded_map, default_zips


def assign_zip_to_segments(df, route_zip_map, default_zips):
    """
    Assign ZIP codes to road segments based on route information.
    
    Strategy:
    1. Match by route_type + route_nbr
    2. For routes crossing multiple ZIPs, use position (CTL_BEGIN_NBR) to estimate location
    3. Fall back to county-based defaults
    """
    
    print("\nAssigning ZIP codes to road segments...")
    
    def get_zip_for_segment(row):
        route_type = str(row.get('route_type', '')).upper() if pd.notna(row.get('route_type')) else ''
        route_nbr = row.get('route_nbr', None)
        if pd.notna(route_nbr):
            try:
                route_nbr = int(float(route_nbr))
            except (ValueError, TypeError):
                route_nbr = None
        county = str(row.get('county', 'FRANKLIN')).upper() if pd.notna(row.get('county')) else 'FRANKLIN'
        ctl_begin = row.get('ctl_begin_nbr', 0)
        try:
            ctl_begin = float(ctl_begin) if pd.notna(ctl_begin) else 0
        except (ValueError, TypeError):
            ctl_begin = 0
        
        # Try route-based mapping
        key = (route_type, route_nbr)
        if key in route_zip_map:
            zip_list = route_zip_map[key]
            
            # If multiple ZIPs, use position as proxy
            if len(zip_list) > 1:
                # Use CTL_BEGIN as rough position indicator
                # Lower CTL numbers = earlier in route
                idx = min(int(ctl_begin / 5), len(zip_list) - 1)  # Rough segmentation
                return str(zip_list[idx])
            else:
                return str(zip_list[0])
        
        # Fall back to county defaults
        if county in default_zips:
            return default_zips[county][0]  # Use first default ZIP
        
        # Last resort: Downtown Columbus
        return '43215'
    
    df['zip_code'] = df.apply(get_zip_for_segment, axis=1)
    
    # Count assignments
    zip_counts = df['zip_code'].value_counts()
    print(f"\n✓ Assigned {df['zip_code'].notna().sum()} segments to ZIP codes")
    print(f"  Unique ZIPs used: {df['zip_code'].nunique()}")
    print(f"\nTop 10 ZIP codes by segment count:")
    print(zip_counts.head(10))
    
    return df


def integrate_zip_occupancy():
    """Main integration function."""
    from backend.core.preprocessing import load_all_data
    
    print("="*70)
    print("ZIP-LEVEL OCCUPANCY DATA INTEGRATION")
    print("="*70)
    
    # Step 1: Load occupancy data
    print("\n[Step 1/4] Loading ZIP-level occupancy data...")
    df_occupancy = load_all_zip_occupancy_files()
    
    if df_occupancy.empty:
        print("\n❌ No occupancy data loaded. Exiting.")
        return None
    
    # Save processed occupancy data
    occupancy_output = Path("backend/data/processed/zip_occupancy_summary.csv")
    occupancy_output.parent.mkdir(parents=True, exist_ok=True)
    df_occupancy.to_csv(occupancy_output, index=False)
    print(f"✓ Saved: {occupancy_output}")
    
    # Step 2: Load traffic data
    print("\n[Step 2/4] Loading traffic data...")
    df_traffic = load_all_data("backend/data", use_merged_2024_2025=True)
    print(f"✓ Loaded {len(df_traffic):,} traffic records")
    print(f"  Years: {sorted(df_traffic['year'].unique())}")
    
    # Step 3: Create route → ZIP mapping
    print("\n[Step 3/4] Creating route-to-ZIP mapping...")
    route_zip_map, default_zips = create_route_to_zip_mapping()
    print(f"✓ Created mapping for {len(route_zip_map)} route patterns")
    
    # Step 4: Assign ZIPs to segments
    print("\n[Step 4/4] Assigning ZIP codes to segments...")
    df_traffic = assign_zip_to_segments(df_traffic, route_zip_map, default_zips)
    
    # Step 5: Merge occupancy data
    print("\n[Step 5/5] Merging occupancy data with traffic...")
    
    # Note: Occupancy data is single-year (latest available)
    # Replicate across all years in traffic data
    years = df_traffic['year'].unique()
    
    occupancy_expanded = pd.concat([
        df_occupancy.assign(year=year) for year in years
    ], ignore_index=True)
    
    df_merged = df_traffic.merge(
        occupancy_expanded,
        on=['zip_code', 'year'],
        how='left',
        suffixes=('', '_zip')
    )
    
    # Check merge success
    matched = df_merged['occupancy_rate'].notna().sum()
    match_pct = (matched / len(df_merged)) * 100
    
    print(f"\n✓ Merge complete:")
    print(f"  Total records: {len(df_merged):,}")
    print(f"  Records with occupancy data: {matched:,} ({match_pct:.1f}%)")
    print(f"  Records missing occupancy: {len(df_merged) - matched:,}")
    
    # Save merged dataset
    merged_output = Path("backend/data/processed/traffic_with_zip_occupancy.csv")
    df_merged.to_csv(merged_output, index=False)
    print(f"\n✓ Saved merged dataset: {merged_output}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    print("\nOccupancy metrics by ZIP (sample):")
    zip_summary = df_merged.groupby('zip_code').agg({
        'occupancy_rate': 'first',
        'total_housing_units': 'first',
        'car_growth_nbr': 'mean'
    }).sort_values('occupancy_rate', ascending=False).head(10)
    print(zip_summary.to_string())
    
    print("\nCorrelation between occupancy and car growth:")
    if 'car_growth_nbr' in df_merged.columns:
        corr = df_merged[['occupancy_rate', 'vacancy_rate', 'total_housing_units', 'car_growth_nbr']].corr()
        print(corr['car_growth_nbr'].drop('car_growth_nbr'))
    
    return df_merged


if __name__ == "__main__":
    df_merged = integrate_zip_occupancy()
    
    if df_merged is not None:
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("\n1. Update backend/train_model.py to include ZIP features:")
        print("   • occupancy_rate")
        print("   • vacancy_rate")
        print("   • total_housing_units")
        print("\n2. Retrain model:")
        print("   python backend/train_model.py")
        print("\n3. Compare R² improvement vs. baseline (0.304)")
        print("="*70 + "\n")
