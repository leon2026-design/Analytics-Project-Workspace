"""
Geocode predictions directly using NLFID from shapefile.
This bypasses the need for CMS data matching.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

# Paths
SHAPEFILE_PATH = Path("backend/data/RoadGeometry/Road Inventory.shp")
PREDICTIONS_DIR = Path("backend/data/predictions/scenarios")
OUTPUT_DIR = Path("backend/data/predictions/scenarios")

print("="*80)
print("GEOCODING PREDICTIONS WITH NLFID")
print("="*80)

# Load shapefile and extract coordinates
print("\nLoading shapefile...")
gdf = gpd.read_file(SHAPEFILE_PATH)

# Convert to WGS84
if str(gdf.crs) != 'EPSG:4326':
    print(f"Converting from {gdf.crs} to EPSG:4326")
    gdf = gdf.to_crs('EPSG:4326')

# Calculate centroids
print("Calculating centroids...")
gdf['centroid'] = gdf.geometry.centroid
gdf['latitude'] = gdf['centroid'].y
gdf['longitude'] = gdf['centroid'].x

# Aggregate coordinates by NLF_ID (take mean of all segments with same ID)
print("Aggregating coordinates by NLF_ID...")
lookup = gdf.groupby('NLF_ID').agg({
    'latitude': 'mean',
    'longitude': 'mean'
}).reset_index()
print(f"Created lookup with {len(lookup):,} unique NLF_IDs (aggregated from {len(gdf):,} segments)")

# Process each prediction file
pred_files = sorted(PREDICTIONS_DIR.glob("predicted_cms_2026_*.csv"))

for pred_file in pred_files:
    print(f"\n{'='*80}")
    print(f"Processing: {pred_file.name}")
    print(f"{'='*80}")
    
    # Load predictions
    pred = pd.read_csv(pred_file)
    print(f"  Loaded {len(pred):,} predictions")
    
    # Check for nlfid column
    if 'nlfid' not in pred.columns:
        print(f"  ⚠ No 'nlfid' column found, skipping...")
        continue
    
    # Merge with lookup
    pred_geo = pred.merge(
        lookup.rename(columns={'NLF_ID': 'nlfid'}),
        on='nlfid',
        how='left'
    )
    
    # Report results
    matched = pred_geo['latitude'].notna().sum()
    print(f"  Matched: {matched:,}/{len(pred):,} ({matched/len(pred)*100:.1f}%)")
    
    # Save
    output_file = OUTPUT_DIR / f"geocoded_{pred_file.name}"
    pred_geo.to_csv(output_file, index=False)
    print(f"  Saved to: {output_file}")

print(f"\n{'='*80}")
print("COMPLETE")
print(f"{'='*80}")
