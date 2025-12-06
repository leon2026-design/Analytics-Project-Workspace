"""
Create GeoJSON file with Franklin County census tracts and employment density.
For use in Dash Leaflet choropleth visualization.
"""

import geopandas as gpd
import pandas as pd
import json

print("Loading census tract boundaries...")
tracts = gpd.read_file('backend/data/census_tracts/tl_2023_39_tract.shp')
tracts = tracts[tracts['COUNTYFP'] == '049']  # Franklin County only
print(f"Loaded {len(tracts)} Franklin County tracts")

print("\nLoading employment data...")
employment = pd.read_csv('backend/data/processed/employment_by_tract_year.csv')
# Use 2022 data (most recent)
employment = employment[employment['year'] == 2022].copy()
employment['tract_id'] = employment['tract'].astype(str).str[-6:]  # Extract 6-digit tract code
employment = employment.rename(columns={'total_jobs': 'C000'})
print(f"Loaded employment data for {len(employment)} tracts (2022)")

print("\nMerging employment with tract boundaries...")
tracts = tracts.merge(employment, left_on='TRACTCE', right_on='tract_id', how='left')

# Calculate employment density (jobs per square mile)
print("\nCalculating employment density...")
tracts_projected = tracts.to_crs('EPSG:3857')  # Project to meters
tracts['area_sqmi'] = tracts_projected.geometry.area / (1609.34**2)
tracts['emp_density'] = tracts['C000'].fillna(0) / tracts['area_sqmi']

# Handle any infinite/nan densities
tracts.loc[tracts['emp_density'].isna(), 'emp_density'] = 0
tracts.loc[tracts['emp_density'] == float('inf'), 'emp_density'] = 0

print(f"Employment density stats:")
print(f"  Min: {tracts['emp_density'].min():.1f} jobs/sqmi")
print(f"  Mean: {tracts['emp_density'].mean():.1f} jobs/sqmi")
print(f"  Max: {tracts['emp_density'].max():.1f} jobs/sqmi")

# Keep only necessary columns for visualization
output_cols = ['GEOID', 'TRACTCE', 'NAME', 'C000', 'area_sqmi', 'emp_density', 'geometry']
tracts_output = tracts[output_cols].copy()

# Convert to GeoJSON
print("\nConverting to GeoJSON...")
geojson = json.loads(tracts_output.to_json())

# Add statistics to properties for legend
max_density = float(tracts['emp_density'].max())
geojson['metadata'] = {
    'min_density': 0,
    'max_density': max_density,
    'num_tracts': len(tracts)
}

output_path = 'backend/data/census_tracts/franklin_tracts_employment.geojson'
with open(output_path, 'w') as f:
    json.dump(geojson, f)

print(f"\nSaved to {output_path}")
print(f"File size: {len(json.dumps(geojson))/1024:.1f} KB")
