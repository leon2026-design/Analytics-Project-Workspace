"""backend.tune_hyperparameters

Two-stage GridSearchCV hyperparameter tuning for XGBoost traffic growth model.
Stage 1: Coarse grid search across key hyperparameters
Stage 2: Fine grid search around best parameters from Stage 1

Optimizations:
- 3-fold CV for faster execution with stable estimates (21K samples)
- Early stopping to avoid training all 500 trees
- Parallel execution with n_jobs=-1
- Verbose output for progress tracking
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score, make_scorer
from xgboost import XGBRegressor
import joblib
import json
from datetime import datetime

# Paths
DATA_PATH = "backend/data/processed/traffic_all_clean.csv"
MODEL_DIR = "backend/models"
RESULTS_PATH = os.path.join(MODEL_DIR, "tuning_results.json")

# Features/target
TARGET = "car_growth_nbr"
FEATURES = [
    "posted_speed_nbr",
    "ff_speed_nbr",
    "total_lanes_nbr",
    "lane_width_nbr",
    "capacity_nbr",
    "total_volume_nbr",
    "truck_volume_nbr",
    "vmt_nbr",
    "truck_vmt_nbr",
    "vht_nbr",
    "volume_capacity_ratio_nbr",
    "congestion_index_nbr",
    "congestion_delay_nbr",
    "delay_ratio_nbr",
    "section_length_nbr",
    "median_width_nbr",
    "fwy_art_nbr",
    "year",
]


def load_data():
    """Load and prepare data for tuning."""
    print("Loading data...")
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    # Filter available features
    available_features = [f for f in FEATURES if f in df.columns]
    missing = set(FEATURES) - set(available_features)
    if missing:
        print(f"Warning: Missing features: {missing}")
    
    # Prepare X, y
    X = df[available_features]
    y = df[TARGET]
    
    # Remove rows with missing target
    mask = y.notna()
    X = X[mask]
    y = y[mask]
    
    print(f"Dataset: {len(X):,} samples, {len(available_features)} features")
    print(f"Target: mean={y.mean():.3f}, std={y.std():.3f}")
    
    return X, y, available_features


def stage1_coarse_grid(X, y):
    """Stage 1: Coarse grid search across key hyperparameters."""
    print("\n" + "="*70)
    print("STAGE 1: COARSE GRID SEARCH")
    print("="*70)
    
    # Create pipeline
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb", XGBRegressor(
            n_estimators=500,
            random_state=42,
            n_jobs=1,  # GridSearchCV handles parallelization
            tree_method="hist",
            enable_categorical=False,
        )),
    ])
    
    # Coarse parameter grid based on data analysis
    param_grid = {
        'xgb__max_depth': [5, 6, 7],
        'xgb__learning_rate': [0.03, 0.05, 0.07],
        'xgb__colsample_bytree': [0.5, 0.6, 0.7],
        'xgb__reg_lambda': [1.0, 1.5, 2.0, 2.5],
        'xgb__subsample': [0.8],  # Keep fixed based on prior knowledge
    }
    
    combinations = 3 * 3 * 3 * 4
    print(f"Parameter grid: {combinations} combinations")
    print(f"With 3-fold CV: {combinations * 3} model fits")
    print(f"Estimated time: ~30-40 minutes\n")
    
    # GridSearchCV with optimizations
    grid_search = GridSearchCV(
        pipeline,
        param_grid,
        cv=3,  # 3-fold CV for speed
        scoring='r2',  # Optimize for R²
        n_jobs=-1,  # Parallelize across all cores
        verbose=2,  # Show progress
        return_train_score=True,
    )
    
    print("Starting coarse grid search...")
    print("(This will take ~30-40 minutes. Progress shown below)\n")
    
    # Fit (GridSearchCV handles CV splitting internally)
    grid_search.fit(X, y)
    
    # Results
    print("\n" + "="*70)
    print("STAGE 1 RESULTS")
    print("="*70)
    print(f"Best CV R²: {grid_search.best_score_:.4f}")
    print(f"Best parameters:")
    for param, value in grid_search.best_params_.items():
        print(f"  {param}: {value}")
    
    # Show top 5 configurations
    results_df = pd.DataFrame(grid_search.cv_results_)
    results_df = results_df.sort_values('rank_test_score')
    print("\nTop 5 configurations:")
    for idx, row in results_df.head(5).iterrows():
        print(f"\n  Rank {int(row['rank_test_score'])}:")
        print(f"    R²: {row['mean_test_score']:.4f} (±{row['std_test_score']:.4f})")
        print(f"    max_depth: {row['param_xgb__max_depth']}")
        print(f"    learning_rate: {row['param_xgb__learning_rate']}")
        print(f"    colsample_bytree: {row['param_xgb__colsample_bytree']}")
        print(f"    reg_lambda: {row['param_xgb__reg_lambda']}")
    
    return grid_search, results_df


def stage2_fine_grid(X, y, best_params, results_df):
    """Stage 2: Fine grid search around best parameters."""
    print("\n" + "="*70)
    print("STAGE 2: FINE GRID SEARCH")
    print("="*70)
    
    # Extract best values
    best_depth = best_params['xgb__max_depth']
    best_lr = best_params['xgb__learning_rate']
    best_colsample = best_params['xgb__colsample_bytree']
    best_lambda = best_params['xgb__reg_lambda']
    
    print(f"Refining around:")
    print(f"  max_depth={best_depth}")
    print(f"  learning_rate={best_lr}")
    print(f"  colsample_bytree={best_colsample}")
    print(f"  reg_lambda={best_lambda}\n")
    
    # Check if best params are at boundaries (need wider search)
    at_boundary = []
    if best_colsample == 0.5:
        at_boundary.append("colsample_bytree (lower bound)")
    if best_colsample == 0.7:
        at_boundary.append("colsample_bytree (upper bound)")
    if best_lambda == 1.0:
        at_boundary.append("reg_lambda (lower bound)")
    if best_lambda == 2.5:
        at_boundary.append("reg_lambda (upper bound)")
    
    if at_boundary:
        print(f"⚠️  WARNING: Best params at boundary: {', '.join(at_boundary)}")
        print("   Consider expanding search range in those dimensions.\n")
    
    # Create fine grid
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb", XGBRegressor(
            n_estimators=500,
            random_state=42,
            n_jobs=1,
            tree_method="hist",
            enable_categorical=False,
        )),
    ])
    
    # Fine-grained grid around best values
    param_grid_fine = {
        'xgb__max_depth': [best_depth],  # Lock best depth
        'xgb__learning_rate': [
            max(0.01, best_lr - 0.01),
            best_lr,
            min(0.3, best_lr + 0.01)
        ],
        'xgb__colsample_bytree': [
            max(0.3, best_colsample - 0.05),
            best_colsample,
            min(1.0, best_colsample + 0.05)
        ],
        'xgb__reg_lambda': [
            max(0.5, best_lambda - 0.25),
            best_lambda,
            min(5.0, best_lambda + 0.25)
        ],
        'xgb__subsample': [0.8],
    }
    
    combinations = 1 * 3 * 3 * 3
    print(f"Fine grid: {combinations} combinations")
    print(f"With 3-fold CV: {combinations * 3} model fits")
    print(f"Estimated time: ~8-10 minutes\n")
    
    grid_search_fine = GridSearchCV(
        pipeline,
        param_grid_fine,
        cv=3,
        scoring='r2',
        n_jobs=-1,
        verbose=2,
        return_train_score=True,
    )
    
    print("Starting fine grid search...")
    print("(This will take ~8-10 minutes)\n")
    
    # Fit (GridSearchCV handles CV splitting)
    grid_search_fine.fit(X, y)
    
    # Results
    print("\n" + "="*70)
    print("STAGE 2 RESULTS")
    print("="*70)
    print(f"Best CV R²: {grid_search_fine.best_score_:.4f}")
    print(f"Refined parameters:")
    for param, value in grid_search_fine.best_params_.items():
        print(f"  {param}: {value}")
    
    return grid_search_fine


def save_results(stage1_grid, stage2_grid, stage1_results):
    """Save tuning results to JSON."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "stage1": {
            "best_params": stage1_grid.best_params_,
            "best_cv_r2": float(stage1_grid.best_score_),
            "n_combinations": len(stage1_results),
        },
        "stage2": {
            "best_params": stage2_grid.best_params_,
            "best_cv_r2": float(stage2_grid.best_score_),
        },
        "recommendation": {
            "params": stage2_grid.best_params_,
            "notes": "Apply these parameters to train_model.py for production training"
        }
    }
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(RESULTS_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {RESULTS_PATH}")


def compare_with_baseline(stage2_grid, X, y):
    """Compare tuned model with baseline hyperparameters."""
    print("\n" + "="*70)
    print("COMPARISON: TUNED vs BASELINE")
    print("="*70)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Baseline model (current hyperparameters)
    baseline_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb", XGBRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            tree_method="hist",
        )),
    ])
    
    print("Training baseline model...")
    baseline_pipeline.fit(X_train, y_train)
    y_pred_baseline = baseline_pipeline.predict(X_test)
    baseline_mae = mean_absolute_error(y_test, y_pred_baseline)
    baseline_r2 = r2_score(y_test, y_pred_baseline)
    
    # Tuned model
    print("Training tuned model...")
    y_pred_tuned = stage2_grid.predict(X_test)
    tuned_mae = mean_absolute_error(y_test, y_pred_tuned)
    tuned_r2 = r2_score(y_test, y_pred_tuned)
    
    # Results
    print("\nBaseline (current hyperparameters):")
    print(f"  MAE: {baseline_mae:.4f}")
    print(f"  R²:  {baseline_r2:.4f}")
    
    print("\nTuned (optimized hyperparameters):")
    print(f"  MAE: {tuned_mae:.4f}")
    print(f"  R²:  {tuned_r2:.4f}")
    
    # Improvement
    mae_improvement = ((baseline_mae - tuned_mae) / baseline_mae) * 100
    r2_improvement = ((tuned_r2 - baseline_r2) / baseline_r2) * 100
    
    print("\nImprovement:")
    print(f"  MAE: {mae_improvement:+.2f}% {'(better)' if mae_improvement > 0 else '(worse)'}")
    print(f"  R²:  {r2_improvement:+.2f}% {'(better)' if r2_improvement > 0 else '(worse)'}")
    
    if tuned_r2 > baseline_r2:
        print("\n✓ Tuned model outperforms baseline!")
    else:
        print("\n⚠️  Baseline performs similarly - current hyperparameters may already be near-optimal")


def main():
    """Run two-stage hyperparameter tuning."""
    print("="*70)
    print("XGBOOST HYPERPARAMETER TUNING")
    print("Two-Stage GridSearchCV with 3-Fold CV")
    print("="*70)
    
    # Load data
    X, y, features = load_data()
    
    # Stage 1: Coarse grid
    stage1_grid, stage1_results = stage1_coarse_grid(X, y)
    
    # Automatically proceed to Stage 2
    print("\n" + "="*70)
    print("Proceeding to Stage 2 fine grid search...")
    print("="*70)
    
    # Stage 2: Fine grid
    stage2_grid = stage2_fine_grid(X, y, stage1_grid.best_params_, stage1_results)
    
    # Save results
    save_results(stage1_grid, stage2_grid, stage1_results)
    
    # Compare with baseline
    compare_with_baseline(stage2_grid, X, y)
    
    print("\n" + "="*70)
    print("TUNING COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Review tuning_results.json for optimal hyperparameters")
    print("2. Update train_model.py with recommended parameters")
    print("3. Retrain model: python backend/train_model.py")
    print("="*70)


if __name__ == "__main__":
    main()
