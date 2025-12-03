# Columbus Traffic Predictor

A machine learning system for predicting traffic growth on Ohio roadways, featuring scenario analysis and an interactive dashboard for exploring future traffic conditions. Built for ODOT District 6 (Columbus area) with support for multi-year data analysis.

## Project Overview

This project predicts car growth percentages on road segments using historical traffic data from ODOT's CMS (Congestion Management System) files. The model learns relationships between traffic conditions (volume, capacity, congestion) and growth patterns, enabling scenario-based forecasting for infrastructure planning.

**Key Features:**
- **XGBoost Model**: Trained on 2019-2023 data with MAE ≈ 0.463 and R² ≈ 0.304
- **Scenario Analysis**: Five 2026 traffic scenarios (baseline, +2%, +5%, +10%, +15% volume growth)
- **Interactive Dashboard**: Dash web application with route search, multi-scenario comparison, and downloadable results
- **Multi-Year Pipeline**: Handles 2019-2025 data with automatic schema harmonization and CSV format matching

## Quick Start

1. **Set up environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   pip install -r requirements.txt
   ```

2. **Train the model:**
   ```powershell
   python backend/train_model.py
   ```

3. **Generate 2026 scenarios:**
   ```powershell
   python backend/predict_scenarios_2026.py
   python backend/visualize_scenarios.py
   ```

4. **Launch the dashboard:**
   ```powershell
   python app/dash_app.py
   ```
   Then open http://localhost:8050 in your browser.

## Project Structure

```
columbus-traffic-predictor/
│
├── app/
│   └── dash_app.py              # Interactive Dash dashboard with scenario explorer
│
├── backend/
│   ├── data/
│   │   ├── processed/           # Cleaned, merged datasets
│   │   ├── predictions/         # Model output files
│   │   └── scenarios/           # 2026 scenario predictions (5 scenarios)
│   ├── models/
│   │   ├── traffic_model.pkl    # Trained XGBoost model + metadata
│   │   ├── feature_importances.* # Feature importance analysis
│   │   └── training_runs.csv    # Training history log
│   ├── preprocessing.py         # Multi-year data loading, schema harmonization, feature engineering
│   ├── train_model.py           # Model training with time-based validation (2019-2023 train / 2024 test)
│   ├── predict.py               # Generic prediction interface
│   ├── predict_2026.py          # 2026 baseline forecasting
│   ├── predict_scenarios_2026.py # Generate 5 traffic scenarios for 2026
│   └── visualize_scenarios.py   # Create comparison charts and distribution plots
│
├── docs/
│   ├── PRESENTATION_GUIDE.md    # Poster presentation guide for research gala
│   └── SCENARIO_ANALYSIS_REPORT.md # Executive summary and findings
│
├── notebooks/
│   └── 01_exploration.ipynb     # Exploratory data analysis
│
├── requirements.txt             # Python dependencies (pandas, xgboost, dash, plotly, etc.)
├── README.md                    # This file
└── .gitignore                   # Excludes data files, models, venv
```

## How It Works

### 1. Data Pipeline
- **Input**: CMS CSV files (2019-2025) placed in `backend/data/`
- **Preprocessing**: 
  - Automatic schema harmonization across years (handles column name variations)
  - CSV format matching (JCRL ↔ NLFID route systems) with 100% success rate for District 6
  - Feature engineering: lag features (car_growth_lag1, total_volume_lag1), rolling averages (2 and 3 period), temporal features (year_norm, year_poly2)
- **Output**: Cleaned datasets in `backend/data/processed/`

### 2. Model Training
- **Algorithm**: XGBoost with 500 trees, depth 6, learning rate 0.05
- **Features** (18 total): Posted speed, free-flow speed, total lanes, capacity, volume, volume-capacity ratio, congestion index, lag features, rolling averages, temporal features
- **Target**: `car_growth_nbr` (percentage change in car traffic)
- **Validation**: Time-based split (train: 2019-2023, test: 2024) with sample weighting by year
- **Performance**: MAE ≈ 0.463, R² ≈ 0.304 on 2024 test data
- **Command**: `python backend/train_model.py`

### 3. Scenario Analysis
The system generates five 2026 traffic scenarios by applying different traffic volume multipliers:
- **Baseline** (0%): No growth assumption, projects current conditions
- **Conservative** (+2%): Minimal recovery scenario
- **Moderate** (+5%): Steady growth
- **Aggressive** (+10%): Strong recovery
- **Post-Pandemic Boom** (+15%): Maximum growth

**Key Finding**: 46.1% of segments show >100% growth at baseline, increasing only to 48.2% at aggressive (+10%) scenario—indicating capacity constraints limit growth potential.

**Commands**:
```powershell
python backend/predict_scenarios_2026.py  # Generate scenarios
python backend/visualize_scenarios.py     # Create comparison charts
```

### 4. Interactive Dashboard
A Dash web application provides:
- **Scenario Explorer**: Compare all 5 scenarios side-by-side
- **Route Search**: Filter by specific route numbers
- **Growth Threshold Slider**: Identify high-growth segments (customizable threshold)
- **Multi-Scenario Comparison**: Overlay up to 3 scenarios with grouped bar charts
- **Data Export**: Download filtered results as CSV
- **Visualizations**: Scatter plots (volume vs growth), histograms (growth distribution), statistics cards

**Launch**: `python app/dash_app.py` → http://localhost:8050

## Key Findings

1. **Infrastructure Stress**: 46% of road segments already exceed 100% car growth capacity at baseline (without any traffic increase)
2. **Capacity Constraints**: Only 2.1 percentage point increase in high-growth segments despite 10% traffic volume increase
3. **Model Behavior**: The model predicts growth based on traffic conditions (volume, congestion, capacity) rather than calendar year—a physics-based approach that enables meaningful scenario comparison
4. **District 6 Focus**: Analysis covers Columbus metropolitan area (ODOT District 6) with 3,570 segments

## Usage Examples

### Train a new model
```powershell
python backend/train_model.py
```

### Generate 2026 baseline forecast
```powershell
python backend/predict_2026.py
```

### Run scenario analysis
```powershell
python backend/predict_scenarios_2026.py
python backend/visualize_scenarios.py
```

### Launch interactive dashboard
```powershell
python app/dash_app.py
# Open browser to http://localhost:8050
```

### Make predictions on new data
```python
from backend.predict import predict_from_csv

predict_from_csv(
    csv_path="backend/data/new_data.csv",
    out_path="backend/data/predictions/output.csv",
    odot_district=6  # or None for all districts
)
```

## Configuration

### Change target district
Default is District 6 (Columbus). To train on all districts:
```python
from backend.train_model import train_model
train_model(odot_district=None)
```

### Adjust scenario parameters
Edit `backend/predict_scenarios_2026.py` to modify:
- Traffic volume multipliers
- Scenario names and descriptions
- Growth thresholds

## Model Insights

### Feature Importance
After training, the model exports feature importance analysis to help understand which factors most influence traffic growth predictions:

**Output Files** (in `backend/models/`):
- `feature_importances.csv`: Sorted table of all features and their importance scores
- `feature_importances.png`: Horizontal bar chart of top 20 features

**Interpretation**:
- Importance scores reflect contribution to reducing prediction error in XGBoost's gradient boosting trees
- Higher values indicate stronger influence on car growth predictions
- Top features typically include: volume-capacity ratio, congestion index, capacity, posted speed, and lag features

**Note**: These are tree-based importances (gain metric), which are fast to compute but can be influenced by feature cardinality and correlation patterns.

## Documentation

- **`docs/PRESENTATION_GUIDE.md`**: Poster presentation guide with elevator pitch, key findings, Q&A prep, and engagement tips
- **`docs/SCENARIO_ANALYSIS_REPORT.md`**: Comprehensive report with executive summary, methodology, insights, and recommendations

## Technical Details

**Dependencies**:
- Python 3.8+
- Core: pandas, numpy, scikit-learn
- ML: xgboost
- Visualization: matplotlib, seaborn, plotly
- Dashboard: dash, dash-bootstrap-components
- Data: joblib (model serialization)

**Data Requirements**:
- CMS CSV files from ODOT (2019-2025)
- Required columns: route identifiers, speed, lanes, capacity, volume, congestion metrics, car growth
- District 6 (Columbus area) currently supported

**Model Specifications**:
- Training samples: 18,179 (2019-2023)
- Test samples: 3,570 (2024)
- Features: 18 engineered features
- Hyperparameters: 500 estimators, max_depth=6, learning_rate=0.05, subsample=0.8
- Validation: Time-based split with year-weighted sampling

## Limitations & Future Work

**Current Limitations**:
- Model captures traffic-condition relationships but not temporal trends (by design)
- R² ≈ 0.30 reflects unmeasured factors (economic conditions, weather, behavior changes)
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

[Specify your license here]

## Contact

For questions or collaboration opportunities, please contact [your contact information].
