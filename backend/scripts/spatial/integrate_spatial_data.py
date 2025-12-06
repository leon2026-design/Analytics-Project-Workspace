"""
Integrate employment and demographic data with geocoded traffic predictions.
Performs spatial joins to add census-based features to road segments.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import numpy as np
from shapely.geometry import Point

def load_census_boundaries():
    """Load census tracts and block groups for Franklin County."""
    
    print("Loading census boundaries...")
    
    # Load census tracts
    tract_path = Path("backend/data/census_tracts/tl_2023_39_tract.shp")
    tracts = gpd.read_file(tract_path)
    
    # Filter to Franklin County (FIPS 39049)
    franklin_tracts = tracts[tracts['COUNTYFP'] == '049'].copy()
    franklin_tracts = franklin_tracts.to_crs('EPSG:4326')  # Ensure WGS84
    
    print(f"  OK Loaded {len(franklin_tracts)} Franklin County census tracts")
    
    # Load block groups if available (finer resolution)
    bg_path = Path("backend/data/census_block_groups/tl_2023_39_bg.shp")
    franklin_bgs = None
    
    if bg_path.exists():
        bgs = gpd.read_file(bg_path)
        franklin_bgs = bgs[bgs['COUNTYFP'] == '049'].copy()
        franklin_bgs = franklin_bgs.to_crs('EPSG:4326')
        print(f"  OK Loaded {len(franklin_bgs)} Franklin County block groups")
    
    return franklin_tracts, franklin_bgs

def aggregate_lodes_employment():
    """Aggregate LODES employment data from census blocks to tracts."""
    
    print("\nAggregating LODES employment data...")
    
    employment_by_year = {}
    
    lodes_files = [
        'backend/employment/oh_wac_S000_JT00_2019.csv',
        'backend/employment/oh_wac_S000_JT00_2020.csv',
        'backend/employment/oh_wac_S000_JT00_2021.csv',
        'backend/employment/oh_wac_S000_JT00_2022.csv'
    ]
    
    for lodes_file in lodes_files:
        year = lodes_file.split('_')[-1].replace('.csv', '')
        
        if not Path(lodes_file).exists():
            print(f"  ⚠ Skipping {year}: File not found")
            continue
        
        print(f"  Processing {year}...")
        lodes = pd.read_csv(lodes_file, dtype={'w_geocode': str})
        
        # Parse census tract from w_geocode
        # Format: SSCCCTTTTTTBBBB (2 state + 3 county + 6 tract + 4 block)
        # Franklin County = 39049
        lodes['state_county'] = lodes['w_geocode'].str[:5]
        lodes['tract_id'] = lodes['w_geocode'].str[5:11]  # 6-digit tract
        lodes['geoid'] = '39049' + lodes['tract_id']  # Match census GEOID format
        
        # Filter to Franklin County
        franklin_lodes = lodes[lodes['state_county'] == '39049'].copy()
        
        print(f"    Franklin County blocks: {len(franklin_lodes):,}")
        
        # Aggregate to tract level
        agg_cols = {
            'C000': 'sum',  # Total jobs
            'CE01': 'sum',  # Earnings $1250/mo or less
            'CE02': 'sum',  # Earnings $1251-3333/mo
            'CE03': 'sum',  # Earnings >$3333/mo
        }
        
        # Add all NAICS industry sectors (CNS01-CNS20)
        for i in range(1, 21):
            col = f'CNS{i:02d}'
            if col in franklin_lodes.columns:
                agg_cols[col] = 'sum'
        
        tract_employment = franklin_lodes.groupby('geoid').agg(agg_cols).reset_index()
        
        # Calculate derived metrics
        tract_employment['pct_high_wage'] = (
            tract_employment['CE03'] / tract_employment['C000']
        ).fillna(0)
        
        # Professional/scientific/technical services
        if 'CNS14' in tract_employment.columns:
            tract_employment['pct_professional'] = (
                tract_employment['CNS14'] / tract_employment['C000']
            ).fillna(0)
        
        employment_by_year[year] = tract_employment
        print(f"    Aggregated to {len(tract_employment)} tracts")
        print(f"    Total jobs: {tract_employment['C000'].sum():,}")
    
    return employment_by_year

def load_occupancy_data():
    """Load ZIP code level occupancy data."""
    
    print("\nLoading housing occupancy data...")
    
    occupancy_dir = Path("backend/data/occupancystatus")
    occupancy_data = {}
    
    for file in occupancy_dir.glob("b25002.*.csv"):
        zipcode = file.stem.split('.')[-1]
        
        df = pd.read_csv(file)
        
        # Extract values (skip label rows)
        total = df[df.iloc[:, 0].str.contains('Total', na=False)].iloc[0, 1]
        occupied = df[df.iloc[:, 0].str.contains('Occupied', na=False)].iloc[0, 1]
        vacant = df[df.iloc[:, 0].str.contains('Vacant', na=False)].iloc[0, 1]
        
        # Remove commas and convert to int
        total_val = int(str(total).replace(',', ''))
        occupied_val = int(str(occupied).replace(',', ''))
        vacant_val = int(str(vacant).replace(',', ''))
        
        occupancy_data[zipcode] = {
            'total_housing_units': total_val,
            'occupied_units': occupied_val,
            'vacant_units': vacant_val,
            'vacancy_rate': vacant_val / total_val if total_val > 0 else 0
        }
    
    print(f"  OK Loaded {len(occupancy_data)} ZIP codes")
    
    return occupancy_data

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance in miles."""
    R = 3956  # Earth radius in miles
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

def calculate_jobs_within_radius(segment_lat, segment_lon, tract_centroids, 
                                 tract_employment, radius_miles=2.0):
    """Calculate total jobs within radius of segment."""
    
    distances = haversine_distance(
        segment_lat, segment_lon,
        tract_centroids['lat'].values,
        tract_centroids['lon'].values
    )
    
    nearby_mask = distances <= radius_miles
    nearby_geoids = tract_centroids[nearby_mask]['geoid'].values
    
    nearby_jobs = tract_employment[
        tract_employment['geoid'].isin(nearby_geoids)
    ]['C000'].sum()
    
    return nearby_jobs

def enrich_predictions(predictions_file, tracts, employment_data, 
                       output_file, year='2022'):
    """Add spatial features to prediction file."""
    
    print(f"\nEnriching {predictions_file.name}...")
    
    # Load predictions
    pred = pd.read_csv(predictions_file)
    
    if 'latitude' not in pred.columns or 'longitude' not in pred.columns:
        print(f"  ⚠ No coordinates found, skipping")
        return
    
    # Create GeoDataFrame
    pred_gdf = gpd.GeoDataFrame(
        pred,
        geometry=gpd.points_from_xy(pred.longitude, pred.latitude),
        crs='EPSG:4326'
    )
    
    print(f"  Loaded {len(pred_gdf):,} predictions")
    
    # Spatial join with census tracts
    pred_enriched = gpd.sjoin(
        pred_gdf, 
        tracts[['GEOID', 'geometry']], 
        how='left', 
        predicate='within'
    )
    
    # Merge employment data
    if year in employment_data:
        tract_employment = employment_data[year]
        
        pred_enriched = pred_enriched.merge(
            tract_employment,
            left_on='GEOID',
            right_on='geoid',
            how='left',
            suffixes=('', '_emp')
        )
        
        print(f"  OK Matched {pred_enriched['C000'].notna().sum():,} segments to employment data")
    
    # Calculate tract centroids for radius calculations
    tract_centroids = tracts.copy()
    tract_centroids['centroid'] = tract_centroids.geometry.centroid
    tract_centroids['lat'] = tract_centroids.centroid.y
    tract_centroids['lon'] = tract_centroids.centroid.x
    tract_centroids = tract_centroids[['GEOID', 'lat', 'lon']].rename(columns={'GEOID': 'geoid'})
    
    # Calculate jobs within 2 miles
    print(f"  Calculating jobs within 2 miles (this may take a minute)...")
    
    tract_emp = employment_data.get(year)
    if tract_emp is not None:
        pred_enriched['jobs_within_2mi'] = pred_enriched.apply(
            lambda row: calculate_jobs_within_radius(
                row['latitude'], row['longitude'],
                tract_centroids, tract_emp, radius_miles=2.0
            ) if pd.notna(row['latitude']) else 0,
            axis=1
        )
    
    # Calculate distance to downtown Columbus
    downtown_lat, downtown_lon = 39.9612, -82.9988
    pred_enriched['distance_to_downtown'] = haversine_distance(
        pred_enriched['latitude'], pred_enriched['longitude'],
        downtown_lat, downtown_lon
    )
    
    # Classify area type
    pred_enriched['area_type'] = pd.cut(
        pred_enriched['distance_to_downtown'],
        bins=[0, 5, 15, 100],
        labels=['Urban Core', 'Suburban', 'Exurban']
    )
    
    # Calculate employment density (jobs per square mile of tract)
    # Approximate using circular area
    if 'C000' in pred_enriched.columns:
        pred_enriched['employment_density'] = pred_enriched['jobs_within_2mi'] / (np.pi * 2**2)
    
    # Drop geometry for CSV output
    output_df = pred_enriched.drop(columns=['geometry', 'index_right'], errors='ignore')
    
    # Save enriched predictions
    output_df.to_csv(output_file, index=False)
    
    print(f"  OK Saved to {output_file}")
    print(f"    Added columns: GEOID (tract), C000 (jobs), distance_to_downtown, jobs_within_2mi, area_type")
    
    # Summary statistics
    if 'jobs_within_2mi' in output_df.columns:
        print(f"\n  Employment Statistics:")
        print(f"    Avg jobs within 2mi: {output_df['jobs_within_2mi'].mean():,.0f}")
        print(f"    Max jobs within 2mi: {output_df['jobs_within_2mi'].max():,.0f}")
        print(f"    Segments near high employment (>10K jobs): {(output_df['jobs_within_2mi'] > 10000).sum():,}")

def main():
    """Main integration pipeline."""
    
    print("="*80)
    print("SPATIAL DATA INTEGRATION PIPELINE")
    print("="*80)
    print("\nThis script adds demographic and employment features to predictions")
    print("by performing spatial joins with census boundaries.\n")
    
    # Load census boundaries
    tracts, block_groups = load_census_boundaries()
    
    # Aggregate employment data
    employment_by_year = aggregate_lodes_employment()
    
    # Load occupancy data
    occupancy_data = load_occupancy_data()
    
    # Enrich all prediction scenarios
    predictions_dir = Path("backend/data/predictions/scenarios")
    enriched_dir = Path("backend/data/predictions/enriched")
    enriched_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n" + "="*80)
    print("ENRICHING PREDICTION FILES")
    print("="*80)
    
    scenario_files = list(predictions_dir.glob("geocoded_predicted_cms_2026_*.csv"))
    
    if not scenario_files:
        print("⚠ No geocoded prediction files found!")
        print("  Expected: backend/data/predictions/scenarios/geocoded_predicted_cms_2026_*.csv")
        return
    
    for pred_file in scenario_files:
        scenario = pred_file.stem.replace('geocoded_predicted_cms_2026_', '')
        output_file = enriched_dir / f"enriched_predicted_cms_2026_{scenario}.csv"
        
        enrich_predictions(
            pred_file, 
            tracts, 
            employment_by_year,
            output_file,
            year='2022'  # Use most recent employment data
        )
    
    print("\n" + "="*80)
    print("INTEGRATION COMPLETE")
    print("="*80)
    print(f"\nEnriched predictions saved to: {enriched_dir}")
    print("\nNext steps:")
    print("1. Update dashboard to use enriched prediction files")
    print("2. Add demographic info to map popups")
    print("3. Create choropleth layers for employment density")
    print("4. Retrain model with spatial features to improve accuracy")

if __name__ == "__main__":
    main()
