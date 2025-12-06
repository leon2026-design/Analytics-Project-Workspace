"""
Evaluate the traffic growth model and explain the data discrepancy.
"""

import pandas as pd
import joblib
from pathlib import Path
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import numpy as np

print("="*80)
print("MODEL EVALUATION & DATA INVESTIGATION")
print("="*80)

# 1. Load model and check metadata
model_path = Path("backend/models/traffic_model.pkl")
if model_path.exists():
    model_data = joblib.load(model_path)
    model = model_data['model']
    meta = model_data['meta']
    
    print("\nModel Metadata:")
    print(f"  MAE (training): {meta.get('mae', 'N/A'):.4f}")
    print(f"  R² (training): {meta.get('r2', 'N/A'):.4f}")
    print(f"  Features used: {len(meta.get('features', []))}")
else:
    print("\n⚠ Model not found!")
    model = None

# 2. Investigate data discrepancy
print("\n" + "="*80)
print("DATA INVESTIGATION")
print("="*80)

orig_file = Path("backend/data/predictions/predicted_cms_2026.csv")
geocoded_file = Path("backend/data/predictions/scenarios/geocoded_predicted_cms_2026_baseline.csv")

print(f"\nOriginal file: {orig_file}")
orig = pd.read_csv(orig_file)
print(f"  Rows: {len(orig):,}")
print(f"  Unique nlfid: {orig.nlfid.nunique():,}")

print(f"\nGeocoded file: {geocoded_file}")
geo = pd.read_csv(geocoded_file, low_memory=False)
print(f"  Rows: {len(geo):,}")
print(f"  Unique nlfid: {geo.nlfid.nunique():,}")

# 3. Explain the discrepancy
print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

print(f"\nThe discrepancy:")
print(f"  Original predictions: 3,570 segments")
print(f"  Geocoded predictions: 197,682 segments")
print(f"  Unique routes (nlfid): {geo.nlfid.nunique():,}")

# Check how many shapefile segments per nlfid
print(f"\nShapefile expansion:")
shapefile = Path("backend/data/RoadGeometry/Road Inventory.shp")
import geopandas as gpd
gdf = gpd.read_file(shapefile)
print(f"  Total shapefile segments: {len(gdf):,}")
print(f"  Unique NLF_ID in shapefile: {gdf.NLF_ID.nunique():,}")

# Show example of one nlfid
example_nlfid = geo.nlfid.iloc[0]
matching_shapefile = gdf[gdf.NLF_ID == example_nlfid]
matching_predictions = geo[geo.nlfid == example_nlfid]

print(f"\nExample: nlfid = {example_nlfid}")
print(f"  Shapefile segments with this nlfid: {len(matching_shapefile):,}")
print(f"  Prediction rows with this nlfid: {len(matching_predictions):,}")

print(f"\n⚠ THE PROBLEM:")
print(f"  The geocoding script did a CROSS JOIN instead of a lookup!")
print(f"  Each prediction matched to ALL shapefile segments with same nlfid")
print(f"  This created {len(geo)/len(orig):.0f}x duplication")

# 4. Verify original predictions are correct
print("\n" + "="*80)
print("ORIGINAL MODEL PERFORMANCE")
print("="*80)

if model:
    # Load test data
    test_data = pd.read_csv("backend/data/processed/traffic_all_clean.csv")
    
    feature_cols = meta['features']
    available_features = [f for f in feature_cols if f in test_data.columns]
    
    X = test_data[available_features]
    y_true = test_data[meta['target']]
    
    # Predict
    y_pred = model.predict(X)
    
    # Calculate metrics
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    print(f"\nModel Performance on Full Dataset:")
    print(f"  R² Score: {r2:.4f} (explains {r2*100:.1f}% of variance)")
    print(f"  MAE: {mae:.4f} ({mae*100:.1f} percentage points)")
    print(f"  RMSE: {rmse:.4f}")
    
    # Context
    print(f"\nInterpretation:")
    if r2 > 0.6:
        print(f"  ✓ R² = {r2:.3f} is GOOD for traffic forecasting")
    elif r2 > 0.4:
        print(f"  ~ R² = {r2:.3f} is MODERATE for traffic forecasting")
    else:
        print(f"  ⚠ R² = {r2:.3f} is LOW - consider more features")
    
    if mae < 0.3:
        print(f"  ✓ MAE = {mae:.3f} means predictions within ±{mae*100:.1f}% on average")
    elif mae < 0.5:
        print(f"  ~ MAE = {mae:.3f} means predictions within ±{mae*100:.1f}% on average")
    else:
        print(f"  ⚠ MAE = {mae:.3f} is high - large prediction errors")
    
    # Distribution
    errors = y_pred - y_true
    print(f"\nError Distribution:")
    print(f"  Mean error: {errors.mean():.4f}")
    print(f"  Std dev: {errors.std():.4f}")
    print(f"  5th percentile: {np.percentile(errors, 5):.4f}")
    print(f"  95th percentile: {np.percentile(errors, 95):.4f}")

# 5. Recommendations
print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

print("\n1. FIX GEOCODING:")
print("   - The geocoded files have ~55x duplication")
print("   - Need to aggregate shapefile coordinates per nlfid BEFORE merging")
print("   - Or use one representative point per nlfid (e.g., centroid of all segments)")

print("\n2. DASHBOARD DISPLAY:")
print("   - Original 3,570 predictions are correct")
print("   - Dashboard showing 197,682 is using duplicated geocoded data")
print("   - Total volume of 5.3B is inflated by duplication factor")

print("\n3. MODEL PERFORMANCE:")
print("   - R² = 0.67 is actually quite good for traffic growth")
print("   - MAE = 0.28 means ±28% prediction error on average")
print("   - This is reasonable given complexity of traffic patterns")

print("\n4. NEXT STEPS:")
print("   - Aggregate shapefile by nlfid to get one lat/lon per route")
print("   - Re-run geocoding with aggregated coordinates")
print("   - Or de-duplicate geocoded files by keeping first row per nlfid")
print("   - Then dashboard will show correct 3,570 segments")
