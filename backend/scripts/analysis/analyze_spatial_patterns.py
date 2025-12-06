"""
Quick spatial analysis: Analyze geocoded traffic by distance to key locations.

This demonstrates what you can do NOW with your geocoded data,
before adding external census tract boundaries.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in miles.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in miles
    r = 3956
    return c * r

def analyze_spatial_patterns():
    """Analyze traffic growth patterns by spatial location."""
    
    print("="*80)
    print("SPATIAL ANALYSIS OF GEOCODED TRAFFIC PREDICTIONS")
    print("="*80)
    
    # Key Columbus locations
    locations = {
        'Downtown Columbus': (39.9612, -82.9988),
        'OSU Campus': (40.0067, -83.0305),
        'Easton Town Center': (40.0506, -82.9188),
        'Polaris': (40.1482, -82.9913),
        'Airport (CMH)': (39.9980, -82.8919),
        'Intel Site (New Albany)': (40.0810, -82.7989),
    }
    
    # Load geocoded baseline predictions
    pred_file = Path("backend/data/predictions/scenarios/geocoded_predicted_cms_2026_baseline.csv")
    
    if not pred_file.exists():
        print(f"⚠ Geocoded predictions not found at {pred_file}")
        print("Run geocode_predictions_nlfid.py first")
        return
    
    df = pd.read_csv(pred_file)
    
    # Filter to valid coordinates
    df = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    
    print(f"\nLoaded {len(df):,} geocoded traffic segments")
    print(f"Coordinate range:")
    print(f"  Latitude: {df['latitude'].min():.4f} to {df['latitude'].max():.4f}")
    print(f"  Longitude: {df['longitude'].min():.4f} to {df['longitude'].max():.4f}")
    
    # Calculate distances to key locations
    for loc_name, (lat, lon) in locations.items():
        col_name = f'dist_to_{loc_name.lower().replace(" ", "_")}_mi'
        df[col_name] = df.apply(
            lambda row: haversine_distance(row['latitude'], row['longitude'], lat, lon),
            axis=1
        )
    
    # Find nearest major location for each segment
    dist_cols = [f'dist_to_{loc.lower().replace(" ", "_")}_mi' for loc in locations.keys()]
    df['nearest_location'] = df[dist_cols].idxmin(axis=1).str.replace('dist_to_', '').str.replace('_mi', '').str.replace('_', ' ').str.title()
    df['distance_to_nearest_mi'] = df[dist_cols].min(axis=1)
    
    # Classify by urban/suburban/rural
    df['area_type'] = pd.cut(
        df['dist_to_downtown_columbus_mi'],
        bins=[0, 5, 15, 100],
        labels=['Urban Core', 'Suburban', 'Exurban']
    )
    
    # Analyze growth by location
    print("\n" + "="*80)
    print("TRAFFIC GROWTH BY DISTANCE TO DOWNTOWN")
    print("="*80)
    
    distance_bins = [0, 3, 6, 10, 15, 100]
    df['distance_bin'] = pd.cut(df['dist_to_downtown_columbus_mi'], bins=distance_bins)
    
    growth_by_distance = df.groupby('distance_bin').agg({
        'predicted_car_growth_nbr': ['mean', 'median', 'count'],
        'total_volume_nbr': 'mean'
    }).round(3)
    
    print(growth_by_distance)
    
    # Analyze by area type
    print("\n" + "="*80)
    print("TRAFFIC GROWTH BY AREA TYPE")
    print("="*80)
    
    growth_by_area = df.groupby('area_type').agg({
        'predicted_car_growth_nbr': ['mean', 'median', 'count'],
        'total_volume_nbr': 'mean',
        'capacity_nbr': 'mean'
    }).round(3)
    
    print(growth_by_area)
    
    # Analyze by nearest major location
    print("\n" + "="*80)
    print("TRAFFIC GROWTH NEAR MAJOR LOCATIONS")
    print("="*80)
    
    # Filter to segments within 3 miles of major locations
    df_near = df[df['distance_to_nearest_mi'] <= 3].copy()
    
    growth_by_location = df_near.groupby('nearest_location').agg({
        'predicted_car_growth_nbr': ['mean', 'median', 'count'],
        'total_volume_nbr': 'mean'
    }).round(3)
    
    print(growth_by_location)
    
    # Find highest growth corridors by location
    print("\n" + "="*80)
    print("TOP 10 HIGHEST GROWTH SEGMENTS")
    print("="*80)
    
    top_growth = df.nlargest(10, 'predicted_car_growth_nbr')
    
    display_cols = ['route_nbr', 'route_type', 'predicted_car_growth_nbr', 
                   'total_volume_nbr', 'nearest_location', 'distance_to_nearest_mi',
                   'latitude', 'longitude']
    available_cols = [c for c in display_cols if c in top_growth.columns]
    
    print(top_growth[available_cols].to_string(index=False))
    
    # Save enriched data
    output_file = Path("backend/data/predictions/scenarios/spatial_analysis_baseline_2026.csv")
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved spatial analysis to: {output_file}")
    
    # Summary insights
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    
    urban_growth = df[df['area_type'] == 'Urban Core']['predicted_car_growth_nbr'].mean()
    suburban_growth = df[df['area_type'] == 'Suburban']['predicted_car_growth_nbr'].mean()
    
    print(f"\n📊 Average predicted growth:")
    print(f"   Urban Core (0-5 mi): {urban_growth*100:.1f}%")
    print(f"   Suburban (5-15 mi): {suburban_growth*100:.1f}%")
    print(f"   Difference: {(suburban_growth-urban_growth)*100:+.1f} percentage points")
    
    # Identify growth hotspots
    high_growth_segments = df[df['predicted_car_growth_nbr'] > df['predicted_car_growth_nbr'].quantile(0.90)]
    
    print(f"\n🚨 High-growth segments (top 10%):")
    print(f"   Count: {len(high_growth_segments)}")
    print(f"   Average growth: {high_growth_segments['predicted_car_growth_nbr'].mean()*100:.1f}%")
    print(f"   Nearest locations:")
    
    hotspot_locations = high_growth_segments['nearest_location'].value_counts().head(3)
    for loc, count in hotspot_locations.items():
        pct = count / len(high_growth_segments) * 100
        print(f"      {loc}: {count} segments ({pct:.1f}%)")

if __name__ == "__main__":
    analyze_spatial_patterns()
