import pandas as pd

df25 = pd.read_csv('backend/data/predictions/predicted_cms_2025.csv')
df26 = pd.read_csv('backend/data/predictions/predicted_cms_2026.csv')

features = [
    'posted_speed_nbr', 'ff_speed_nbr', 'total_lanes_nbr', 'lane_width_nbr',
    'capacity_nbr', 'total_volume_nbr', 'truck_volume_nbr', 'vmt_nbr',
    'truck_vmt_nbr', 'vht_nbr', 'volume_capacity_ratio_nbr',
    'congestion_index_nbr', 'congestion_delay_nbr', 'delay_ratio_nbr',
    'section_length_nbr', 'year', 'year_norm', 'year_poly2'
]

print('Feature comparison (first 3 rows):')
print('='*80)
for i in range(min(3, len(df25))):
    print(f'\nRow {i}:')
    for f in features:
        val25 = df25[f].iloc[i]
        val26 = df26[f].iloc[i]
        same = abs(val25 - val26) < 1e-6
        print(f'  {f:30s} 2025: {val25:12.6f}  2026: {val26:12.6f}  {"✓" if same else "✗ DIFF"}')
    
    pred25 = df25['predicted_car_growth_nbr'].iloc[i]
    pred26 = df26['predicted_car_growth_nbr'].iloc[i]
    print(f'  {"predicted_car_growth_nbr":30s} 2025: {pred25:12.6f}  2026: {pred26:12.6f}  {"✓" if abs(pred25-pred26)<1e-6 else "✗ DIFF"}')

print('\n' + '='*80)
print('\nSummary:')
print(f'2025 shape: {df25.shape}')
print(f'2026 shape: {df26.shape}')
print(f'Predictions identical: {(df25["predicted_car_growth_nbr"] == df26["predicted_car_growth_nbr"]).all()}')
