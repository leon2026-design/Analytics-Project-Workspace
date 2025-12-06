"""
Comprehensive model audit to diagnose R² drop from 0.669 to 0.304.
Checks: feature set, data quality, train/test split, preprocessing consistency.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib

print("="*80)
print("MODEL PERFORMANCE AUDIT")
print("="*80)

# ============================================================================
# 1. LOAD CURRENT MODEL AND CHECK METADATA
# ============================================================================
print("\n[1] CURRENT MODEL INSPECTION")
print("-"*80)

model_path = Path("backend/models/traffic_model.pkl")
if model_path.exists():
    model_data = joblib.load(model_path)
    model = model_data.get('model')
    meta = model_data.get('meta', {})
    
    print(f"Current model performance:")
    print(f"  R² = {meta.get('r2', 'N/A'):.4f}")
    print(f"  MAE = {meta.get('mae', 'N/A'):.4f}")
    print(f"  Target: {meta.get('target', 'N/A')}")
    print(f"  Features ({len(meta.get('features', []))}): {meta.get('features', [])}")
    
    current_r2 = float(meta.get('r2', 0))
    current_features = meta.get('features', [])
else:
    print("ERROR: Model file not found!")
    current_r2 = 0
    current_features = []

# ============================================================================
# 2. ANALYZE HISTORICAL BEST PERFORMANCE
# ============================================================================
print("\n[2] HISTORICAL BEST PERFORMANCE")
print("-"*80)

runs_file = Path("backend/models/training_runs.csv")
if runs_file.exists():
    # Read line by line to handle inconsistent CSV
    with open(runs_file, 'r') as f:
        lines = f.readlines()
    
    header = lines[0].strip().split(',')
    best_r2 = 0
    best_run = None
    
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) >= 8:
            try:
                r2 = float(parts[-1])
                if r2 > best_r2:
                    best_r2 = r2
                    best_run = {
                        'timestamp': parts[0],
                        'features': parts[4].split(';') if ';' in parts[4] else [],
                        'r2': r2,
                        'mae': float(parts[-2])
                    }
            except:
                continue
    
    if best_run:
        print(f"Best historical run (R² = {best_run['r2']:.4f}):")
        print(f"  Date: {best_run['timestamp']}")
        print(f"  MAE: {best_run['mae']:.4f}")
        print(f"  Features ({len(best_run['features'])}): {best_run['features']}")
        
        best_features = set(best_run['features'])
        current_features_set = set(current_features)
        
        print(f"\nFeature comparison:")
        print(f"  Best model: {len(best_features)} features")
        print(f"  Current model: {len(current_features_set)} features")
        
        added = current_features_set - best_features
        removed = best_features - current_features_set
        
        if added:
            print(f"  ✓ Added to current: {added}")
        if removed:
            print(f"  ✗ Removed from current: {removed}")
        
        performance_gap = (best_run['r2'] - current_r2) * 100
        print(f"\n** PERFORMANCE GAP: {performance_gap:.1f} percentage points **")

# ============================================================================
# 3. CHECK TRAINING DATA QUALITY
# ============================================================================
print("\n[3] TRAINING DATA QUALITY CHECK")
print("-"*80)

data_path = Path("backend/data/processed/traffic_all_clean.csv")
if data_path.exists():
    df = pd.read_csv(data_path)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Date range: {df['year'].min():.0f} - {df['year'].max():.0f}" if 'year' in df.columns else "No year column")
    
    # Check target variable
    if 'car_growth_nbr' in df.columns:
        target = df['car_growth_nbr']
        print(f"\nTarget variable (car_growth_nbr):")
        print(f"  Missing: {target.isna().sum()} ({target.isna().sum()/len(df)*100:.1f}%)")
        print(f"  Mean: {target.mean():.4f}")
        print(f"  Std: {target.std():.4f}")
        print(f"  Min: {target.min():.4f}, Max: {target.max():.4f}")
        print(f"  Outliers (|z|>3): {(np.abs((target - target.mean()) / target.std()) > 3).sum()}")
    
    # Check for features
    print(f"\nFeature availability in data:")
    missing_features = []
    for feat in current_features:
        if feat not in df.columns:
            missing_features.append(feat)
        else:
            missing_pct = df[feat].isna().sum() / len(df) * 100
            if missing_pct > 20:
                print(f"  WARNING: {feat} has {missing_pct:.1f}% missing values")
    
    if missing_features:
        print(f"  ERROR: Features not in data: {missing_features}")
    
    # Check train/test split
    if 'year' in df.columns:
        train_mask = (df['year'] >= 2019) & (df['year'] <= 2023)
        test_mask = df['year'] >= 2024
        
        print(f"\nTrain/test split (2019-2023 train, 2024+ test):")
        print(f"  Train rows: {train_mask.sum()}")
        print(f"  Test rows: {test_mask.sum()}")
        print(f"  Split ratio: {train_mask.sum()/test_mask.sum():.1f}:1")
        
        if test_mask.sum() < 100:
            print(f"  WARNING: Very small test set ({test_mask.sum()} rows)")
        
        # Check if target distribution differs between train/test
        train_target_mean = df[train_mask]['car_growth_nbr'].mean()
        test_target_mean = df[test_mask]['car_growth_nbr'].mean()
        print(f"  Train target mean: {train_target_mean:.4f}")
        print(f"  Test target mean: {test_target_mean:.4f}")
        print(f"  Distribution shift: {abs(train_target_mean - test_target_mean):.4f}")
        
        if abs(train_target_mean - test_target_mean) > 0.1:
            print(f"  WARNING: Significant distribution shift between train/test!")

else:
    print("ERROR: Processed data file not found!")

# ============================================================================
# 4. CHECK FEATURE CORRELATIONS
# ============================================================================
print("\n[4] FEATURE CORRELATION WITH TARGET")
print("-"*80)

if data_path.exists() and current_features:
    df = pd.read_csv(data_path)
    
    if 'car_growth_nbr' in df.columns:
        # Calculate correlations for all features
        correlations = []
        for feat in current_features:
            if feat in df.columns:
                valid = df[[feat, 'car_growth_nbr']].dropna()
                if len(valid) > 0:
                    corr = valid[feat].corr(valid['car_growth_nbr'])
                    correlations.append((feat, corr, abs(corr)))
        
        correlations.sort(key=lambda x: x[2], reverse=True)
        
        print(f"Top 10 correlated features:")
        for feat, corr, abs_corr in correlations[:10]:
            print(f"  {feat:30s} r={corr:7.4f}")
        
        weak_features = [f for f, c, ac in correlations if ac < 0.05]
        if weak_features:
            print(f"\nWARNING: {len(weak_features)} features with |r| < 0.05 (very weak):")
            for feat in weak_features[:5]:
                print(f"  - {feat}")
            if len(weak_features) > 5:
                print(f"  ... and {len(weak_features)-5} more")

# ============================================================================
# 5. CHECK PREPROCESSING CONSISTENCY
# ============================================================================
print("\n[5] PREPROCESSING CONSISTENCY CHECK")
print("-"*80)

# Check if SimpleImputer strategy is consistent
if model:
    imputer = model.named_steps.get('imputer')
    if imputer:
        print(f"Imputation strategy: {imputer.strategy}")
        print(f"Features imputed: {len(imputer.statistics_)}")
    
    xgb = model.named_steps.get('xgb')
    if xgb:
        print(f"\nXGBoost configuration:")
        print(f"  n_estimators: {xgb.n_estimators}")
        print(f"  learning_rate: {xgb.learning_rate}")
        print(f"  max_depth: {xgb.max_depth}")
        print(f"  subsample: {xgb.subsample}")
        print(f"  colsample_bytree: {xgb.colsample_bytree}")
        print(f"  reg_lambda: {xgb.reg_lambda}")

# ============================================================================
# 6. FEATURE ENGINEERING CHECK
# ============================================================================
print("\n[6] FEATURE ENGINEERING AUDIT")
print("-"*80)

engineered_features = [f for f in current_features if 'year_' in f or 'median_width' in f]
if engineered_features:
    print(f"Engineered/derived features found: {engineered_features}")
    
    if 'year' in current_features and any('year_' in f for f in current_features):
        print("\nWARNING: Both 'year' and engineered year features present!")
        print("This could cause multicollinearity issues.")
else:
    print("No obvious engineered features detected.")

# ============================================================================
# 7. SUMMARY AND RECOMMENDATIONS
# ============================================================================
print("\n" + "="*80)
print("AUDIT SUMMARY")
print("="*80)

issues_found = []

if performance_gap > 30:
    issues_found.append(f"CRITICAL: {performance_gap:.1f} point R² drop from best model")

if added:
    issues_found.append(f"Feature set changed: added {added}")

if removed:
    issues_found.append(f"Feature set changed: removed {removed}")

if weak_features and len(weak_features) > 5:
    issues_found.append(f"{len(weak_features)} features with |r| < 0.05 (adding noise)")

if data_path.exists():
    df = pd.read_csv(data_path)
    if 'year' in df.columns:
        test_mask = df['year'] >= 2024
        if test_mask.sum() < 100:
            issues_found.append(f"Small test set ({test_mask.sum()} rows)")

if issues_found:
    print("\nISSUES IDENTIFIED:")
    for i, issue in enumerate(issues_found, 1):
        print(f"  {i}. {issue}")
else:
    print("\n✓ No major issues detected")

print("\nRECOMMENDATIONS:")
print("  1. Remove weak features (year_norm, year_poly2) - test without engineered year features")
print("  2. Verify train/test split matches best model configuration")
print("  3. Consider hyperparameter tuning if issues 1-2 don't improve R²")
print("  4. Check for data leakage or preprocessing bugs")
print("\n" + "="*80)
