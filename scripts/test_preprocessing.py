"""Test updated preprocessing with merged 2024-2025 data."""

from backend.preprocessing import load_all_data

print("Loading all data with merged 2024-2025...")
df = load_all_data('backend/data')

print("\n=== Year Distribution ===")
print(df['year'].value_counts().sort_index())

print(f"\n=== Summary ===")
print(f"Total rows: {len(df)}")

if 'odot_district' in df.columns:
    d6_count = (df['odot_district'] == 6).sum()
    print(f"District 6 rows: {d6_count}")
    
    print("\n=== District 6 by Year ===")
    df_d6 = df[df['odot_district'] == 6]
    print(df_d6['year'].value_counts().sort_index())
    
    print("\n=== Car Growth Stats by Year (District 6) ===")
    if 'car_growth_nbr' in df_d6.columns:
        stats = df_d6.groupby('year')['car_growth_nbr'].agg(['count', 'mean', 'std'])
        print(stats)

print("\n=== Source Files ===")
if 'source_file' in df.columns:
    print(df['source_file'].value_counts())
