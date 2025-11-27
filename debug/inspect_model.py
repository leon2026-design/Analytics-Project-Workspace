import joblib
import pandas as pd
import numpy as np

# Load model
bundle = joblib.load('backend/models/traffic_model.pkl')
model = bundle['model']
meta = bundle.get('meta', {})

print("Model pipeline steps:")
for name, step in model.named_steps.items():
    print(f"  {name}: {type(step).__name__}")

print("\nModel type:", type(model.named_steps['xgb']))

# Get the XGBoost regressor
xgb_model = model.named_steps['xgb']

print("\nXGBoost parameters:")
print(f"  n_estimators: {xgb_model.n_estimators}")
print(f"  max_depth: {xgb_model.max_depth}")
print(f"  learning_rate: {xgb_model.learning_rate}")

# Test prediction with manual feature variation
features = meta.get('features', [])
print(f"\nFeatures ({len(features)}):", features)

# Load a sample 2025 row
df_2025 = pd.read_csv('backend/data/predictions/predicted_cms_2025.csv')
sample = df_2025[features].iloc[0:1].copy()

print("\nSample row features:")
for f in ['year', 'year_norm', 'year_poly2']:
    if f in sample.columns:
        print(f"  {f}: {sample[f].iloc[0]}")

# Predict with original values
pred_original = model.predict(sample)
print(f"\nOriginal prediction: {pred_original[0]:.6f}")

# Now manually change year features to 2026 values
sample_2026 = sample.copy()
if 'year' in sample_2026.columns:
    sample_2026['year'] = 2026
if 'year_norm' in sample_2026.columns:
    sample_2026['year_norm'] = 1.166667
if 'year_poly2' in sample_2026.columns:
    sample_2026['year_poly2'] = 1.361111

pred_2026 = model.predict(sample_2026)
print(f"2026 prediction: {pred_2026[0]:.6f}")
print(f"Difference: {pred_2026[0] - pred_original[0]:.6f}")

# Test each time feature individually
print("\nIsolated feature impact tests:")
for time_feat in ['year', 'year_norm', 'year_poly2']:
    if time_feat in sample.columns:
        test_sample = sample.copy()
        original_val = test_sample[time_feat].iloc[0]
        test_sample[time_feat] = test_sample[time_feat] * 1.5  # 50% increase
        pred_test = model.predict(test_sample)
        print(f"  {time_feat}: {original_val:.3f} -> {test_sample[time_feat].iloc[0]:.3f}, pred: {pred_original[0]:.6f} -> {pred_test[0]:.6f}, diff: {pred_test[0] - pred_original[0]:.6f}")
