"""Quick test of JCRL matching logic."""

import pandas as pd
import re

# Test JCRL cleaning
test_jcrls = [
    'SADASR00032**C    0 ',
    'SADASR00032**C  334 ',
    'SWOOUS00006**C17505',
    'SWOOIR00070**C30120'
]

print("JCRL Cleaning Test:")
print("=" * 60)
for jcrl in test_jcrls:
    # Remove trailing digits and spaces
    cleaned = re.sub(r'\s*\d+\s*$', '', jcrl.strip()).strip()
    
    # Extract route type and number
    m = re.search(r'([A-Z]{2})(\d{5})', cleaned)
    if m:
        route_type = m.group(1)
        route_nbr = int(m.group(2))
        print(f"{jcrl:30s} -> {cleaned:20s} ({route_type}, {route_nbr})")
    else:
        print(f"{jcrl:30s} -> {cleaned:20s} (NO MATCH)")

# Quick sample from actual files
print("\n" + "=" * 60)
print("Loading sample rows from actual files...")

df_2024 = pd.read_csv("backend/data/24CarGrowthData(CMS5).csv", nrows=100)
df_2025 = pd.read_csv("backend/data/CMS_2025.csv", nrows=100)

print(f"\n2024 sample JCRL values (first 5):")
for jcrl in df_2024['JCRL'].head(5):
    cleaned = re.sub(r'\s*\d+\s*$', '', str(jcrl).strip()).strip()
    print(f"  {repr(jcrl):40s} -> {repr(cleaned)}")

print(f"\n2025 sample NLFID values (first 5):")
for nlfid in df_2025['NLFID'].head(5):
    print(f"  {nlfid}")

print(f"\n2025 sample ROUTE info (first 5):")
sample_routes = df_2025[['NLFID', 'ROUTE_TYPE', 'ROUTE_NBR']].head(5)
print(sample_routes.to_string(index=False))
