"""
Deduplicate geocoded prediction files.
Keeps only the first row per unique prediction (first occurrence).
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("DEDUPLICATING GEOCODED PREDICTION FILES")
print("="*80)

# Input/output directories
input_dir = Path("backend/data/predictions/scenarios")
output_dir = Path("backend/data/predictions/scenarios_fixed")
output_dir.mkdir(exist_ok=True, parents=True)

# Process each geocoded file
geocoded_files = sorted(input_dir.glob("geocoded_predicted_cms_2026_*.csv"))

for file in geocoded_files:
    print(f"\n{'='*80}")
    print(f"Processing: {file.name}")
    print(f"{'='*80}")
    
    # Load
    df = pd.read_csv(file, low_memory=False)
    print(f"  Original rows: {len(df):,}")
    
    # Identify duplicate key columns (all columns except lat/lon which vary)
    # Use first 20 original columns as the unique identifier
    key_cols = [col for col in df.columns[:90] if col not in ['latitude', 'longitude', 'geometry']]
    
    # Keep first occurrence of each unique prediction
    df_dedup = df.drop_duplicates(subset=key_cols, keep='first')
    
    print(f"  Deduplicated rows: {len(df_dedup):,}")
    print(f"  Removed duplicates: {len(df) - len(df_dedup):,}")
    
    # Calculate volume change
    orig_volume = df['total_volume_nbr'].sum()
    dedup_volume = df_dedup['total_volume_nbr'].sum()
    print(f"  Original total volume: {orig_volume:,.0f}")
    print(f"  Deduplicated total volume: {dedup_volume:,.0f}")
    print(f"  Reduction factor: {orig_volume/dedup_volume:.1f}x")
    
    # Save deduplicated version
    output_file = output_dir / file.name
    df_dedup.to_csv(output_file, index=False)
    print(f"  ✓ Saved to: {output_file}")

print("\n" + "="*80)
print("DEDUPLICATION COMPLETE")
print("="*80)
print(f"\nFixed files saved to: {output_dir}")
print("Next: Move these to scenarios/ directory to replace originals")
