"""
Spatial join of geocoded traffic predictions with demographic and employment data.

Now that traffic segments have lat/lon coordinates, we can:
1. Match segments to census tracts/ZIP codes
2. Enrich predictions with population, housing, employment data
3. Analyze correlation between demographics and traffic growth
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.geometry import Point

# Paths
PREDICTIONS_DIR = Path("backend/data/predictions/scenarios")
DEMOGRAPHICS_DIR = Path("backend/data")
OUTPUT_DIR = Path("backend/data/predictions/scenarios")

def load_census_tract_boundaries():
    """
    Load census tract boundaries shapefile for Franklin County.
    
    You'll need to download this from Census TIGER/Line:
    https://www.census.gov/cgi-bin/geo/shapefiles/index.php
    - Select Year: 2023
    - Select Layer: Census Tracts
    - Select State: Ohio
    - Select County: Franklin
    
    Save to: backend/data/census_tracts/
    """
    tract_path = Path("backend/data/census_tracts/tl_2023_39_tract.shp")
    
    if not tract_path.exists():
        print(f"⚠ Census tract shapefile not found at {tract_path}")
        print("Download from: https://www.census.gov/cgi-bin/geo/shapefiles/index.php")
        return None
    
    gdf = gpd.read_file(tract_path)
    
    # Filter to Franklin County (FIPS: 39049)
    gdf = gdf[gdf['COUNTYFP'] == '049'].copy()
    
    # Ensure WGS84 projection
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs('EPSG:4326')
    
    print(f"Loaded {len(gdf)} census tracts for Franklin County")
    return gdf

def load_demographic_data():
    """Load ACS demographic data by ZIP code."""
    # Use your existing integrate_acs_data.py functions
    import sys
    sys.path.append('backend')
    from integrate_acs_data import load_all_acs_demographics
    
    return load_all_acs_demographics()

def load_employment_data():
    """
    Load employment data by location.
    
    Options:
    1. LEHD Origin-Destination Employment Statistics (LODES)
       - Download from: https://lehd.ces.census.gov/data/
       - Provides job counts by census block
    
    2. County Business Patterns
       - From Census Bureau
       - Employment by industry and location
    
    3. InfoUSA/ReferenceUSA business data
       - If you have institutional access
    """
    employment_file = Path("backend/data/employment/lodes_franklin_county.csv")
    
    if not employment_file.exists():
        print(f"⚠ Employment data not found at {employment_file}")
        print("Consider downloading LODES data from: https://lehd.ces.census.gov/data/")
        return None
    
    df = pd.read_csv(employment_file)
    return df

def spatial_join_predictions_with_demographics():
    """
    Main function: Join geocoded traffic predictions with demographic/employment data.
    """
    print("="*80)
    print("SPATIAL ENRICHMENT OF TRAFFIC PREDICTIONS")
    print("="*80)
    
    # Load census tract boundaries
    print("\n1. Loading census tract boundaries...")
    census_tracts = load_census_tract_boundaries()
    
    if census_tracts is None:
        print("\nℹ️  To enable spatial analysis, download census tract boundaries.")
        print("Meanwhile, using ZIP code-based demographic matching...")
        return match_by_zip_code()
    
    # Load demographic data
    print("\n2. Loading demographic data...")
    demographics = load_demographic_data()
    
    # Load employment data
    print("\n3. Loading employment data...")
    employment = load_employment_data()
    
    # Process each geocoded prediction file
    print("\n4. Processing geocoded predictions...")
    pred_files = sorted(PREDICTIONS_DIR.glob("geocoded_predicted_cms_2026_*.csv"))
    
    for pred_file in pred_files:
        print(f"\n{'='*80}")
        print(f"Processing: {pred_file.name}")
        print(f"{'='*80}")
        
        # Load predictions
        pred = pd.read_csv(pred_file)
        
        # Check if already geocoded
        if 'latitude' not in pred.columns or 'longitude' not in pred.columns:
            print(f"  ⚠ No coordinates found, skipping...")
            continue
        
        # Filter to segments with valid coordinates
        pred_valid = pred[pred['latitude'].notna() & pred['longitude'].notna()].copy()
        print(f"  Valid coordinates: {len(pred_valid):,}/{len(pred):,}")
        
        # Convert to GeoDataFrame
        geometry = [Point(lon, lat) for lon, lat in zip(pred_valid['longitude'], pred_valid['latitude'])]
        gdf_pred = gpd.GeoDataFrame(pred_valid, geometry=geometry, crs='EPSG:4326')
        
        # Spatial join with census tracts
        print(f"  Performing spatial join with census tracts...")
        gdf_enriched = gpd.sjoin(gdf_pred, census_tracts, how='left', predicate='within')
        
        # Add tract-level demographics
        if demographics is not None:
            # Match demographics by year and tract
            print(f"  Adding demographic data...")
            # This is a simplified example - adjust based on your demographic data structure
            # gdf_enriched = gdf_enriched.merge(demographics, on=['year', 'tract'], how='left')
        
        # Add employment data
        if employment is not None:
            print(f"  Adding employment data...")
            # Match employment by census block or tract
            # gdf_enriched = gdf_enriched.merge(employment, on='tract', how='left')
        
        # Calculate new features
        print(f"  Calculating spatial features...")
        
        # Distance to downtown Columbus (39.9612, -82.9988)
        downtown = Point(-82.9988, 39.9612)
        gdf_enriched['distance_to_downtown_mi'] = gdf_enriched.geometry.distance(downtown) * 69  # degrees to miles
        
        # Classify urban/suburban/rural based on distance
        gdf_enriched['area_type'] = pd.cut(
            gdf_enriched['distance_to_downtown_mi'],
            bins=[0, 5, 15, 100],
            labels=['Urban', 'Suburban', 'Rural']
        )
        
        # Save enriched predictions
        output_file = OUTPUT_DIR / pred_file.name.replace('geocoded_', 'enriched_')
        gdf_enriched.drop(columns=['geometry'], errors='ignore').to_csv(output_file, index=False)
        print(f"  Saved to: {output_file}")
        
        # Show sample enrichment
        print(f"\n  Sample enriched data:")
        sample_cols = ['route_nbr', 'predicted_car_growth_nbr', 'latitude', 'longitude', 
                      'distance_to_downtown_mi', 'area_type']
        available_cols = [c for c in sample_cols if c in gdf_enriched.columns]
        print(gdf_enriched[available_cols].head(3).to_string(index=False))

def match_by_zip_code():
    """
    Simpler approach: Match traffic segments to ZIP codes without spatial join.
    Uses approximate ZIP code assignment based on coordinates.
    """
    print("\n" + "="*80)
    print("ZIP CODE-BASED DEMOGRAPHIC MATCHING")
    print("="*80)
    
    # Load your ZIP code to demographic mapping from occupancystatus files
    zip_files = sorted(Path("backend/data/occupancystatus").glob("b25002.*.csv"))
    
    print(f"\nFound {len(zip_files)} ZIP code demographic files")
    
    # For each geocoded prediction file
    pred_files = sorted(PREDICTIONS_DIR.glob("geocoded_predicted_cms_2026_*.csv"))
    
    for pred_file in pred_files:
        print(f"\nProcessing: {pred_file.name}")
        pred = pd.read_csv(pred_file)
        
        if 'latitude' not in pred.columns:
            continue
        
        # Use reverse geocoding or ZIP code boundaries to assign ZIPs
        # For now, this is a placeholder showing the approach
        print(f"  Loaded {len(pred):,} predictions")
        print(f"  With coordinates: {pred['latitude'].notna().sum():,}")
        
        # TODO: Add reverse geocoding to get ZIP codes from lat/lon
        # Options:
        # 1. Use geopy library with Nominatim
        # 2. Use ZIP code boundary shapefile
        # 3. Use Census geocoding API
        
    print("\nTo enable full spatial analysis:")
    print("1. Download census tract boundaries (see load_census_tract_boundaries)")
    print("2. Download LODES employment data (see load_employment_data)")
    print("3. Run this script again")

if __name__ == "__main__":
    spatial_join_predictions_with_demographics()
