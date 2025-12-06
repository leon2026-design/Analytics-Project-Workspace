"""
Add latitude/longitude coordinates to prediction CSV files.

Reads geocoded CMS data and joins it with prediction files based on segment IDs.
"""

import pandas as pd
from pathlib import Path

# Paths
GEOCODED_CMS = Path("backend/data/geocoded/geocoded_CMS5_2023(in).csv")
PREDICTIONS_DIR = Path("backend/data/predictions")
SCENARIOS_DIR = PREDICTIONS_DIR / "scenarios"

def load_geocoded_coords():
    """Load the geocoded CMS data with lat/lon."""
    print(f"Loading geocoded CMS data from: {GEOCODED_CMS}")
    cms_df = pd.read_csv(GEOCODED_CMS)
    
    # Keep only the columns we need: A, B, JCRL, latitude, longitude
    coords_df = cms_df[['A', 'B', 'JCRL', 'latitude', 'longitude']].copy()
    
    # Report match rate
    total = len(coords_df)
    matched = coords_df['latitude'].notna().sum()
    print(f"  Total segments: {total:,}")
    print(f"  With coordinates: {matched:,} ({matched/total*100:.1f}%)")
    
    return coords_df

def add_coords_to_file(pred_file, coords_df):
    """Add coordinates to a prediction file."""
    print(f"\nProcessing: {pred_file.name}")
    
    # Load prediction file
    pred_df = pd.read_csv(pred_file)
    print(f"  Loaded {len(pred_df):,} predictions")
    
    # Check if coordinates already exist
    if 'latitude' in pred_df.columns and 'longitude' in pred_df.columns:
        print(f"  ⚠ Coordinates already exist, skipping...")
        return
    
    # Merge with coordinates
    # The key question is: what columns in pred_df match with A, B, JCRL in coords_df?
    # Let's check what columns are available
    print(f"  Available columns: {', '.join(pred_df.columns[:10])}...")
    
    # Try to find matching columns (handle both uppercase and lowercase)
    if 'A' in pred_df.columns and 'B' in pred_df.columns:
        print("  Merging on columns A and B...")
        pred_with_coords = pred_df.merge(
            coords_df[['A', 'B', 'latitude', 'longitude']],
            on=['A', 'B'],
            how='left'
        )
    elif 'a' in pred_df.columns and 'b' in pred_df.columns:
        print("  Merging on columns a and b (renaming to A and B)...")
        coords_renamed = coords_df.rename(columns={'A': 'a', 'B': 'b'})
        pred_with_coords = pred_df.merge(
            coords_renamed[['a', 'b', 'latitude', 'longitude']],
            on=['a', 'b'],
            how='left'
        )
    elif 'JCRL' in pred_df.columns:
        print("  Merging on JCRL column...")
        pred_with_coords = pred_df.merge(
            coords_df[['JCRL', 'latitude', 'longitude']],
            on='JCRL',
            how='left'
        )
    elif 'jcrl' in pred_df.columns:
        print("  Merging on jcrl column (renaming to JCRL)...")
        coords_renamed = coords_df.rename(columns={'JCRL': 'jcrl'})
        pred_with_coords = pred_df.merge(
            coords_renamed[['jcrl', 'latitude', 'longitude']],
            on='jcrl',
            how='left'
        )
    else:
        print("  ⚠ No matching columns found (A/B/a/b or JCRL/jcrl), skipping...")
        return
    
    # Report merge results
    total = len(pred_with_coords)
    with_coords = pred_with_coords['latitude'].notna().sum()
    print(f"  Merge results: {with_coords:,}/{total:,} predictions have coordinates ({with_coords/total*100:.1f}%)")
    
    # Save updated file
    output_file = pred_file.parent / f"geocoded_{pred_file.name}"
    pred_with_coords.to_csv(output_file, index=False)
    print(f"  Saved to: {output_file}")

def main():
    """Main pipeline."""
    print("="*80)
    print("ADD COORDINATES TO PREDICTIONS")
    print("="*80)
    
    # Load geocoded coordinates
    coords_df = load_geocoded_coords()
    
    # Process scenario files
    print("\n" + "="*80)
    print("Processing scenario files...")
    print("="*80)
    
    scenario_files = sorted(SCENARIOS_DIR.glob("predicted_cms_2026_*.csv"))
    for scenario_file in scenario_files:
        add_coords_to_file(scenario_file, coords_df)
    
    # Process other prediction files
    print("\n" + "="*80)
    print("Processing other prediction files...")
    print("="*80)
    
    other_files = [
        PREDICTIONS_DIR / "predicted_2024.csv",
        PREDICTIONS_DIR / "predicted_cms_2025.csv",
        PREDICTIONS_DIR / "predicted_cms_2026.csv",
    ]
    
    for pred_file in other_files:
        if pred_file.exists():
            add_coords_to_file(pred_file, coords_df)
    
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print("\nGeocoded prediction files have been created with 'geocoded_' prefix.")
    print("Next steps:")
    print("1. Review the geocoded prediction files")
    print("2. Update the dashboard to use these geocoded files")
    print("3. Test the Leaflet map with real coordinates")

if __name__ == "__main__":
    main()
