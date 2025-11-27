import pandas as pd

df = pd.read_csv('backend/data/CMS_D6_2024_2025_merged.csv')
print(f'Total rows: {len(df)}')
print(f'Unique NLFID: {df["NLFID"].nunique()}')

# Check for duplicates
dups = df.duplicated(subset=['NLFID', 'STL_BEGIN_NBR', 'STL_END_NBR']).sum()
print(f'Duplicate rows: {dups}')

# Show a sample
print('\nFirst 5 rows:')
print(df[['NLFID', 'ROUTE_TYPE', 'ROUTE_NBR', 'CAR_GROWTH_NBR', 'car_growth_2024']].head())
