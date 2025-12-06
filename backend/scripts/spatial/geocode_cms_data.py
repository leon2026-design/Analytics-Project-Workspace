"""
Geocode CMS traffic data by matching with ODOT Road Inventory shapefile.

Matches CMS segments to shapefile geometries using CTL/STL values,
then extracts centroid coordinates for each segment.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import re

# Paths
SHAPEFILE_PATH = Path("backend/data/RoadGeometry/Road Inventory.shp")
CMS_DIR = Path("backend/data")
OUTPUT_DIR = Path("backend/data/geocoded")
OUTPUT_DIR.mkdir(exist_ok=True)

def load_shapefile():
    """Load and prepare the Road Inventory shapefile."""
    print("Loading shapefile...")
    gdf = gpd.read_file(SHAPEFILE_PATH)
    
    # Keep only columns we need to save memory
    needed_cols = ['CTL_BEGIN_', 'CTL_END_NB', 'geometry']
    gdf = gdf[needed_cols].copy()
    
    # Convert to WGS84 for lat/lon
    if str(gdf.crs) != 'EPSG:4326':
        print(f"Converting from {gdf.crs} to EPSG:4326 (WGS84)")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Extract coordinates from centroids
    print("Calculating centroids...")
    gdf['centroid'] = gdf.geometry.centroid
    gdf['latitude'] = gdf['centroid'].y
    gdf['longitude'] = gdf['centroid'].x
    
    # Drop geometry columns we don't need anymore
    gdf = gdf.drop(columns=['geometry', 'centroid'])
    
    print(f"Loaded {len(gdf):,} road segments")
    print(f"Coordinate ranges:")
    print(f"  Latitude: {gdf['latitude'].min():.6f} to {gdf['latitude'].max():.6f}")
    print(f"  Longitude: {gdf['longitude'].min():.6f} to {gdf['longitude'].max():.6f}")
    
    return gdf

def parse_jcrl_column(jcrl_str):
    """
    Parse JCRL column to extract CTL value in miles.
    Format appears to be: SADASR00032**C  658
    Where the number at the end is the CTL position in FEET.
    Shapefile CTL values are in MILES, so we convert.
    """
    if pd.isna(jcrl_str):
        return None
    
    # Extract the last number from the string (in feet)
    match = re.search(r'(\d+)\s*$', str(jcrl_str).strip())
    if match:
        feet = float(match.group(1))
        miles = feet / 5280.0  # Convert feet to miles
        return miles
    return None

def geocode_cms_file(cms_file, shapefile_gdf):
    """Geocode a single CMS file by matching with shapefile."""
    print(f"\n{'='*80}")
    print(f"Processing: {cms_file.name}")
    print(f"{'='*80}")
    
    # Load CMS data
    cms_df = pd.read_csv(cms_file)
    print(f"Loaded {len(cms_df):,} CMS records")
    
    # Parse JCRL to get CTL values
    print("Parsing JCRL column...")
    cms_df['ctl_value'] = cms_df['JCRL'].apply(parse_jcrl_column)
    
    valid_ctl = cms_df['ctl_value'].notna().sum()
    print(f"Extracted CTL values for {valid_ctl:,} records ({valid_ctl/len(cms_df)*100:.1f}%)")
    
    # Match using vectorized operations for speed
    print("Matching CMS segments with shapefile geometries...")
    
    # Initialize columns
    cms_df['latitude'] = None
    cms_df['longitude'] = None
    
    # Process in batches to avoid memory issues
    batch_size = 1000
    total_batches = (len(cms_df) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(cms_df))
        batch = cms_df.iloc[start_idx:end_idx]
        
        if (batch_idx + 1) % 10 == 0:
            print(f"  Processing batch {batch_idx+1}/{total_batches}...")
        
        for idx in batch.index:
            ctl = cms_df.at[idx, 'ctl_value']
            if pd.isna(ctl):
                continue
            
            # Find matching shapefile segments
            matches = shapefile_gdf[
                (shapefile_gdf['CTL_BEGIN_'] <= ctl) & 
                (shapefile_gdf['CTL_END_NB'] >= ctl)
            ]
            
            if len(matches) > 0:
                # Use first match or average if multiple
                lat = matches['latitude'].iloc[0] if len(matches) == 1 else matches['latitude'].mean()
                lon = matches['longitude'].iloc[0] if len(matches) == 1 else matches['longitude'].mean()
                cms_df.at[idx, 'latitude'] = lat
                cms_df.at[idx, 'longitude'] = lon
    
    # Report matching success
    matched_count = cms_df['latitude'].notna().sum()
    match_rate = matched_count / len(cms_df) * 100
    print(f"\nMatching results:")
    print(f"  Matched: {matched_count:,} ({match_rate:.1f}%)")
    print(f"  Unmatched: {len(cms_df) - matched_count:,}")
    
    # Save geocoded file
    output_file = OUTPUT_DIR / f"geocoded_{cms_file.name}"
    cms_df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    
    return cms_df, match_rate

def main():
    """Main geocoding pipeline."""
    print("="*80)
    print("CMS DATA GEOCODING")
    print("="*80)
    
    # Load shapefile once
    shapefile_gdf = load_shapefile()
    
    # Find all CMS files
    cms_files = sorted(CMS_DIR.glob("CMS5_*.csv"))
    print(f"\nFound {len(cms_files)} CMS files to process")
    
    results = []
    for cms_file in cms_files:
        geocoded_df, match_rate = geocode_cms_file(cms_file, shapefile_gdf)
        results.append({
            'file': cms_file.name,
            'records': len(geocoded_df),
            'matched': geocoded_df['latitude'].notna().sum(),
            'match_rate': match_rate
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("GEOCODING SUMMARY")
    print(f"{'='*80}")
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    print(f"\nGeocoded files saved to: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Review the geocoded files in backend/data/geocoded/")
    print("2. Use these files in your predictions to add lat/lon to scenario outputs")
    print("3. Update the dashboard to use the real coordinates on the Leaflet map")

if __name__ == "__main__":
    main()
