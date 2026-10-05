"""Debug preprocessing loading."""

from backend.core.preprocessing import load_data, clean_data
import glob
import os

pattern = os.path.join("backend/data", "*.csv")
files = sorted(glob.glob(pattern))

# Filter like preprocessing does
merged_file = "backend/data/CMS_D6_2024_2025_merged.csv"
if os.path.exists(merged_file):
    exclude_patterns = ['24CarGrowthData', 'CMS_2025.csv', 'CMS_2026.csv']
    files = [f for f in files if not any(ex in os.path.basename(f) for ex in exclude_patterns)]
    files.append(merged_file)

print("Files to be loaded:")
for f in files:
    base = os.path.basename(f)
    print(f"  {base}")
    
    # Check if it matches merged pattern
    if 'merged' in base.lower() and '2024' in base and '2025' in base:
        print(f"    -> Detected as merged file")
        df = load_data(f)
        df = clean_data(df)
        print(f"    -> Rows after load/clean: {len(df)}")
