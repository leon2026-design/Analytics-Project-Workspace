"""
Process the Road Inventory shapefile to extract segment coordinates.

This script:
1. Loads the ODOT Road Inventory shapefile
2. Extracts geometry (linestrings) for each road segment
3. Calculates centroid coordinates (lat/lon)
4. Exports the geocoded road inventory
"""

import geopandas as gpd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Paths
SHAPEFILE_PATH = Path("backend/data/RoadGeometry/Road Inventory.shp")
OUTPUT_DIR = Path("backend/data/geocoded")
OUTPUT_DIR.mkdir(exist_ok=True)

def load_shapefile():
    """Load the Road Inventory shapefile."""
    print(f"Loading shapefile from: {SHAPEFILE_PATH}")
    gdf = gpd.read_file(SHAPEFILE_PATH)
    print(f"✓ Loaded {len(gdf):,} road segments")
    print(f"✓ CRS: {gdf.crs}")
    print(f"\nColumns available:")
    for col in gdf.columns:
        print(f"  - {col}")
    return gdf

def extract_coordinates(gdf):
    """Extract centroid coordinates from geometries."""
    print("\nExtracting coordinates...")
    
    # Convert to WGS84 (EPSG:4326) for lat/lon
    if gdf.crs and gdf.crs != 'EPSG:4326':
        print(f"Converting from {gdf.crs} to EPSG:4326 (WGS84)")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Calculate centroids
    gdf['centroid'] = gdf.geometry.centroid
    gdf['latitude'] = gdf['centroid'].y
    gdf['longitude'] = gdf['centroid'].x
    
    print(f"✓ Extracted coordinates for {len(gdf):,} segments")
    print(f"  Lat range: {gdf['latitude'].min():.6f} to {gdf['latitude'].max():.6f}")
    print(f"  Lon range: {gdf['longitude'].min():.6f} to {gdf['longitude'].max():.6f}")
    
    return gdf

def explore_shapefile_columns(gdf):
    """Display sample data to identify CTL/STL columns."""
    print("\n" + "="*80)
    print("SHAPEFILE DATA PREVIEW")
    print("="*80)
    
    # Show first 5 rows of key columns (if they exist)
    potential_cols = [col for col in gdf.columns if any(
        key in col.upper() for key in ['CTL', 'STL', 'ROUTE', 'SECTION', 'ID', 'NBR']
    )]
    
    if potential_cols:
        print("\nKey columns found:")
        print(gdf[potential_cols].head(10))
    else:
        print("\nFirst 10 rows of all non-geometry columns:")
        non_geom_cols = [col for col in gdf.columns if col not in ['geometry', 'centroid']]
        print(gdf[non_geom_cols].head(10))
    
    print(f"\nData types:")
    for col in gdf.columns:
        if col not in ['geometry', 'centroid']:
            print(f"  {col}: {gdf[col].dtype}")

def save_geocoded_data(gdf):
    """Save processed data with coordinates."""
    # Drop geometry columns for CSV export
    output_df = gdf.copy()
    output_df = output_df.drop(columns=['geometry', 'centroid'], errors='ignore')
    
    # Save as CSV
    output_csv = OUTPUT_DIR / "road_inventory_geocoded.csv"
    output_df.to_csv(output_csv, index=False)
    print(f"\n✓ Saved geocoded data to: {output_csv}")
    print(f"  {len(output_df):,} rows × {len(output_df.columns)} columns")
    
    # Also save the GeoDataFrame with geometry
    output_gpkg = OUTPUT_DIR / "road_inventory.gpkg"
    gdf.to_file(output_gpkg, driver='GPKG')
    print(f"✓ Saved GeoPackage to: {output_gpkg}")
    
    return output_csv

def main():
    """Main processing pipeline."""
    print("="*80)
    print("ODOT Road Inventory Shapefile Processing")
    print("="*80)
    
    # Load shapefile
    gdf = load_shapefile()
    
    # Extract coordinates
    gdf = extract_coordinates(gdf)
    
    # Explore columns
    explore_shapefile_columns(gdf)
    
    # Save results
    output_file = save_geocoded_data(gdf)
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE!")
    print("="*80)
    print(f"\nNext steps:")
    print(f"1. Review the output file: {output_file}")
    
    return gdf

if __name__ == "__main__":
    main()
