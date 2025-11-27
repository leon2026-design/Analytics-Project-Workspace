"""Test if NLFID and cleaned JCRL can match on route info."""

import pandas as pd
import re

df_2024 = pd.read_csv("backend/data/24CarGrowthData(CMS5).csv", nrows=1000)
df_2025 = pd.read_csv("backend/data/CMS_2025.csv", nrows=1000)

# Clean 2024 JCRL
df_2024['jcrl_clean'] = df_2024['JCRL'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', str(x).strip()).strip())
df_2024['route_24'] = df_2024['jcrl_clean'].apply(lambda x: re.search(r'([A-Z]{2})(\d{5})', x))
df_2024['rtype_24'] = df_2024['route_24'].apply(lambda m: m.group(1) if m else None)
df_2024['rnbr_24'] = df_2024['route_24'].apply(lambda m: int(m.group(2)) if m else None)

# Extract from 2025 NLFID
df_2025['route_25'] = df_2025['NLFID'].apply(lambda x: re.search(r'([A-Z]{2})(\d{5})', str(x)))
df_2025['rtype_25'] = df_2025['route_25'].apply(lambda m: m.group(1) if m else None)
df_2025['rnbr_25'] = df_2025['route_25'].apply(lambda m: int(m.group(2)) if m else None)

print("2024 Route extraction (first 10):")
print(df_2024[['jcrl_clean', 'rtype_24', 'rnbr_24']].head(10).to_string(index=False))

print("\n2025 Route extraction (first 10):")
print(df_2025[['NLFID', 'ROUTE_TYPE', 'ROUTE_NBR', 'rtype_25', 'rnbr_25']].head(10).to_string(index=False))

# Check if extracted values match provided columns
match_rate = (df_2025['rtype_25'] == df_2025['ROUTE_TYPE']).sum() / len(df_2025) * 100
print(f"\nNLFID extraction matches ROUTE_TYPE column: {match_rate:.1f}%")

match_rate = (df_2025['rnbr_25'] == df_2025['ROUTE_NBR']).sum() / len(df_2025) * 100
print(f"NLFID extraction matches ROUTE_NBR column: {match_rate:.1f}%")

# Find common routes
routes_24 = set(zip(df_2024['rtype_24'].dropna(), df_2024['rnbr_24'].dropna()))
routes_25 = set(zip(df_2025['ROUTE_TYPE'].dropna(), df_2025['ROUTE_NBR'].dropna()))

common = routes_24.intersection(routes_25)
print(f"\nCommon routes in sample: {len(common)} out of {len(routes_24)} (2024) and {len(routes_25)} (2025)")
print(f"Sample common routes: {list(common)[:5]}")
