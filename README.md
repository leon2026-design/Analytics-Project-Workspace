# Columbus Traffic Predictor

Traffic growth prediction system for Columbus District 6 using XGBoost regression with demographic and spatial features.

## Project Overview

Predicts vehicle growth on Columbus District 6 road segments using an XGBoost regression pipeline with traffic, road-inventory, and temporal features.

**Key Features:**
- **XGBoost pipeline**: train and evaluate metrics from the data available locally
- **5 Scenarios**: baseline → post_pandemic_boom (1.0×-1.15× volume growth)
- **Interactive Dashboard**: Dash + Plotly with geocoded map visualization
- **Organized Structure**: Modular codebase with core ML modules and utility scripts

## Quick Start

1. **Train production model:**
   ```powershell
   python backend/core/train_model.py
   ```
   Training data is not committed to the repository. First place the required CMS
   CSV files in `backend/data/`.

2. **Generate 2026 predictions:**
   ```powershell
   python backend/scripts/predictions/predict_scenarios_2026.py
   ```

3. **Launch dashboard:**
   ```powershell
   python app/dash_app.py
   ```
   Open http://127.0.0.1:8050/

## Project Structure

```
columbus-traffic-predictor/
│
├── backend/
│   ├── core/                          # Core ML and data modules
│   │   ├── preprocessing.py           # Data loading, cleaning, feature engineering
│   │   ├── train_model.py             # Production model training
│   │   ├── predict.py                 # Prediction interface for trained model
│   │   └── tune_hyperparameters.py    # GridSearchCV hyperparameter optimization
│   │
│   ├── scripts/
│   │   ├── predictions/               # Scenario prediction generators
│   │   │   ├── predict_2026.py        # Single baseline 2026 prediction
│   │   │   └── predict_scenarios_2026.py  # 5 scenarios (baseline→post_pandemic_boom)
│   │   │
│   │   ├── spatial/                   # Geocoding and spatial processing
│   │   │   ├── geocode_cms_data.py    # Geocode CMS traffic data
│   │   │   ├── geocode_predictions_nlfid.py  # Geocode predictions by NLFID
│   │   │   ├── add_coords_to_predictions.py  # Add lat/lon to prediction CSVs
│   │   │   ├── download_census_boundaries.py # Download census geometries
│   │   │   ├── process_shapefile.py   # Convert shapefiles to GeoJSON
│   │   │   ├── integrate_spatial_data.py     # Merge spatial features
│   │   │   └── create_employment_geojson.py  # Generate employment overlays
│   │   │
│   │   ├── data_processing/           # Data integration pipelines
│   │   │   ├── enrich_with_demographics.py   # Add census demographics
│   │   │   ├── integrate_acs_data.py          # ACS demographic integration
│   │   │   ├── integrate_employment_county.py # County employment data
│   │   │   ├── integrate_lodes_employment.py  # LODES employment data
│   │   │   ├── integrate_zip_occupancy.py     # ZIP occupancy data
│   │   │   ├── match_cms_2024_2025.py         # Match CMS yearly data
│   │   │   └── deduplicate_geocoded_files.py  # Clean geocoding duplicates
│   │   │
│   │   └── analysis/                  # Model evaluation and visualization
│   │       ├── audit_model.py         # Model performance auditing
│   │       ├── analyze_enriched_predictions.py  # Prediction statistics
│   │       ├── analyze_spatial_patterns.py      # Spatial correlation analysis
│   │       ├── evaluate_model_and_data.py       # Data quality evaluation
│   │       └── visualize_scenarios.py           # Scenario comparison plots
│   │
│   ├── data/
│   │   ├── raw/                       # Original data sources
│   │   ├── processed/                 # Cleaned and feature-engineered data
│   │   └── predictions/               # Generated predictions
│   │       ├── scenarios/             # 5 scenario CSVs
│   │       └── enriched/              # Geocoded predictions with demographics
│   │
│   └── models/
│       ├── traffic_model.pkl          # Trained XGBoost model
│       └── tuning_results.json        # GridSearchCV results
│
├── app/
│   └── dash_app.py                    # Dashboard visualization (Dash + Plotly)
│
└── docs/
    └── analysis/                      # Technical documentation
```

## Import Guidelines

All files now use the organized module structure:

**Core modules:**
```python
from backend.core.preprocessing import load_all_data, coerce_numeric
from backend.core.predict import predict_from_dataframe
from backend.core.train_model import main as train_model
```

**Utility scripts:**
```python
# Predictions
from backend.scripts.predictions.predict_scenarios_2026 import generate_scenarios

# Data processing
from backend.scripts.data_processing.integrate_acs_data import integrate_demographics_into_traffic

# Analysis
from backend.scripts.analysis.analyze_enriched_predictions import analyze_predictions
```

## Model Details

### Current Training Hyperparameters
```python
{
    'n_estimators': 500,
    'learning_rate': 0.07,        # ↑ from 0.05 (faster learning)
    'max_depth': 7,               # ↑ from 6 (more complexity)
    'subsample': 0.8,             # Unchanged
    'colsample_bytree': 0.5,      # ↓ from 0.8 (addresses multicollinearity)
    'reg_lambda': 1.25,           # ↑ from 1.0 (more regularization)
    'random_state': 42,
    'tree_method': 'hist'
}
```

Run training and holdout evaluation on the current dataset before relying on a
reported score. Tuning uses cross-validation on the training partition and
compares the selected estimator against an untouched holdout set.

### Feature Set (18 features)
```python
FEATURES = [
    'posted_speed_nbr', 'ff_speed_nbr', 'total_lanes_nbr',
    'lane_width_nbr', 'capacity_nbr', 'total_volume_nbr',
    'truck_volume_nbr', 'vmt_nbr', 'truck_vmt_nbr', 'vht_nbr',
    'volume_capacity_ratio_nbr', 'congestion_index_nbr',
    'congestion_delay_nbr', 'delay_ratio_nbr', 'section_length_nbr',
    'median_width_nbr', 'fwy_art_nbr', 'year'
]
```

Target: `car_growth_nbr` (change in vehicle throughput 2024→2026)

## Development Workflow

### Adding New Features
1. Modify `backend/core/preprocessing.py` to engineer feature
2. Update `FEATURES` list in `backend/core/train_model.py`
3. Update `FEATURES` list in `backend/core/predict.py` (must match)
4. Retrain: `python backend/core/train_model.py`
5. Regenerate predictions: `python backend/scripts/predictions/predict_scenarios_2026.py`

### Tuning Hyperparameters
```bash
python backend/core/tune_hyperparameters.py
```
Runs two-stage GridSearchCV:
- **Stage 1**: Coarse grid (108 combinations, ~30 min)
- **Stage 2**: Fine grid around best params (27 combinations, ~10 min)

Results saved to `backend/models/tuning_results.json`. Copy optimal params to `train_model.py`.

### Adding New Scenarios
Edit `backend/scripts/predictions/predict_scenarios_2026.py`:
```python
SCENARIOS = {
    'your_scenario': {
        'volume_multiplier': 1.10,  # 10% volume growth
        'description': 'Your description'
    }
}
```

## Data Pipeline

1. **Raw data** → `backend/data/raw/`
   - CMS traffic data (2024 baseline)
   - Census ACS demographics
   - Employment data (LODES, county)

2. **Preprocessing** → `backend/core/preprocessing.py`
   - Clean missing values
   - Engineer features (capacity ratios, cyclical time)
   - Merge spatial/demographic attributes

3. **Model training** → `backend/core/train_model.py`
   - 80/20 train/test split
   - XGBoost with optimized hyperparameters
   - Save to `backend/models/traffic_model.pkl`

4. **Prediction generation** → `backend/scripts/predictions/`
   - Apply scenarios to 2024 baseline
   - Generate 2026 forecasts (5 scenarios × 3,570 segments)

5. **Geocoding** → `backend/scripts/spatial/`
   - Add latitude/longitude via NLFID lookup
   - Save to `backend/data/predictions/enriched/`

6. **Dashboard** → `app/dash_app.py`
   - Load enriched predictions
   - Visualize on interactive map

## Key Insights

### Model Behavior
- **Infrastructure-driven**: Predictions emphasize road capacity over volume inputs
- **Weak scenario sensitivity**: 90-92% avg growth across all volume scenarios (weak 2% range)
- **High-growth segments**: 35% of segments predicted >100% growth
- **Spatial clustering**: High-growth areas concentrated in northwest/southwest Columbus

### Performance Evolution
| Stage | R² | MAE | Change |
|-------|-----|-----|--------|
| Initial | 0.304 | 0.550 | Baseline |
| Feature fix | 0.646 | 0.400 | +112% R² |
| Hyperparameter tuning | 0.701 | 0.351 | +8.5% R² |

### Data Characteristics
- **Samples**: 21,749 (District 6 road segments across years)
- **Multicollinearity**: 24 feature pairs with |r| > 0.7
- **Missing data**: <5% after median imputation
- **Target distribution**: Right-skewed (median growth = 0.89, mean = 0.94)

## Troubleshooting

**Import errors after reorganization:**
- Verify imports use `backend.core.*` or `backend.scripts.*` paths
- Check no old files remain in flat `backend/` directory

**Prediction mismatch:**
- Ensure `FEATURES` list matches between `train_model.py` and `predict.py`
- Verify model trained on same features as prediction input

**Dashboard not loading:**
- Confirm predictions exist in `backend/data/predictions/enriched/`
- Check geocoded files have `latitude` and `longitude` columns
- Verify all 5 scenario files present

**Tuning takes too long:**
- Reduce `n_estimators` in grid (default: 500)
- Decrease `cv` folds (default: 3)
- Use coarser grid spacing

## Contact & Contribution

Project maintained for Columbus traffic forecasting. For questions about:
- **Model methodology**: See `backend/core/train_model.py` comments
- **Feature engineering**: See `backend/core/preprocessing.py` docstrings
- **Prediction scenarios**: See `backend/scripts/predictions/predict_scenarios_2026.py`
- **Dashboard customization**: See `app/dash_app.py`

---

**Last Updated**: 2025-12-06 (Hyperparameter optimization + project reorganization)

**Dependencies**:
- Python 3.10+
- Core: pandas, numpy, scikit-learn, joblib
- ML: xgboost (v1.7.x)
- Visualization: matplotlib, plotly
- Dashboard: dash, dash-leaflet, dash-bootstrap-components
- Spatial: shapely, geopandas

**Model Specifications**:
- Training samples: depend on the CMS files supplied locally (80/20 random split)
- Features: 18 traffic, road-inventory, and temporal features
- Hyperparameters: 500 estimators, max_depth=7, learning_rate=0.07, colsample_bytree=0.5, reg_lambda=1.25
- Performance: calculate from the current training run's holdout set

## License

MIT License - See LICENSE file for details

**Current Limitations**:
- Model captures traffic-condition relationships but not temporal trends (by design)
- Validate performance against an untouched holdout set before using forecasts for planning
- District 6 focus—other districts may have different patterns

**Potential Enhancements**:
- Two-stage forecasting: (1) predict traffic volumes, (2) predict growth given volumes
- Geographic mapping with lat/lon visualization
- Real-time data integration
- Multi-district comparison tools
- Custom scenario builder in dashboard
- Time-series trend analysis
- Cloud deployment (Heroku, Render, AWS)

## License

© 2025 Traffic Gang. Creative Commons

## Contact

For questions or collaboration opportunities, please contact Leon Gonzales (gonzales.260@osu.edu) or Willie Tenney(tenney.62@osu.edu) .
