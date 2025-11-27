# 2026 Prediction Audit Summary

## Issue
Predictions for 2026 are identical to 2025 despite `year_norm` and `year_poly2` changing correctly.

## Root Cause Analysis

### 1. Time Features ARE Computing Correctly
- 2025: `year_norm=1.0`, `year_poly2=1.0`
- 2026: `year_norm=1.167`, `year_poly2=1.361`
- ✅ The `recompute_2026_time_features` function works as intended

### 2. Model Has Time Features BUT They Have No Effect
Feature importances show non-zero values:
- `year`: 0.072 (3rd most important)
- `year_poly2`: 0.053 (9th)
- `year_norm`: 0.049 (10th)

However, **manual prediction tests show ZERO sensitivity** to time feature changes:
- Changing `year` from 2025 → 3037: prediction unchanged
- Changing `year_norm` from 1.0 → 1.5: prediction unchanged
- Changing `year_poly2` from 1.0 → 1.5: prediction unchanged

### 3. Why This Happened

The model (XGBoost with 500 trees, depth=6, lr=0.05) learned that time features have no predictive power because:

**Hypothesis A: Multicollinearity/Redundancy**
- The model has THREE correlated time features: `year`, `year_norm`, `year_poly2`
- XGBoost may have learned to ignore them due to redundancy with other stronger predictors
- Feature importance ≠ actual marginal effect in tree models

**Hypothesis B: Training Data Pattern**
Year distribution shows:
```
Year  Count  Mean Car Growth
2019  4240   1.21
2020  3377   0.91
2021  3434   0.78
2022  3567   0.79
2023  3561   0.70
2024  3570   0.78
2025  3570   0.78
```

Training used 2019-2023 (train) vs 2024-2025 (test). The model may have learned:
1. Traffic metrics (volume, congestion, etc.) are better predictors than year
2. Temporal trend is weak or non-monotonic (2019 high, then decline, then plateau)
3. Year features correlate with other features that capture the same information

**Hypothesis C: Model Saturation**
- XGBoost trees may have fully split on traffic/geometry features
- Time features never made it into the top splits
- Feature importance reflects training set variance, not test set predictive power

## Recommendations

### Option 1: Retrain with Stronger Temporal Signal (Recommended)
```python
# In train_model.py, modify features to use ONLY year_norm
FEATURES = [
    "posted_speed_nbr",
    "ff_speed_nbr",
    # ... other features ...
    "year_norm",  # Keep only this one time feature
]

# Consider adding interaction features
df["volume_x_year"] = df["total_volume_nbr"] * df["year_norm"]
df["congestion_x_year"] = df["congestion_index_nbr"] * df["year_norm"]
```

### Option 2: Use a Different Model Architecture
- Try Linear Regression or Ridge to see if time features matter
- Compare coefficients and p-values

### Option 3: Feature Engineering for 2026
If the model truly learned that traffic patterns don't change with time, then to get different 2026 predictions, you need to change the **traffic features** themselves:
```python
# In predict_2026.py, apply growth factors to traffic features
df_2026_d6["total_volume_nbr"] *= 1.02  # 2% growth
df_2026_d6["truck_volume_nbr"] *= 1.015  # 1.5% growth
# Recompute derived metrics
df_2026_d6["volume_capacity_ratio_nbr"] = df_2026_d6["total_volume_nbr"] / df_2026_d6["capacity_nbr"]
```

### Option 4: Inspect Model Decision Path
```python
# See what features XGBoost actually uses for predictions
from xgboost import plot_tree
plot_tree(xgb_model, num_trees=0)  # visualize first tree
```

## Next Steps

1. **Verify the issue is model-learned, not code bug**: ✅ CONFIRMED
   - Time features compute correctly
   - Model receives correct feature values
   - Model simply learned time has no effect

2. **Decide on approach**:
   - Accept that model predicts based on current traffic state, not year
   - Retrain with different features/architecture
   - Manually adjust 2026 input traffic volumes to reflect expected growth

3. **Document model behavior**:
   - This model predicts car growth based on **current traffic conditions**
   - It does NOT extrapolate temporal trends
   - For future projections, adjust input traffic metrics, not just year
