# Columbus Traffic Predictor

This is a starter Python project workspace. Replace this README with project-specific details as you develop your application.

## Getting Started

1. Ensure you have Python 3.8+ installed.
2. (Recommended) Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```
3. Install dependencies (if any):
   ```powershell
   pip install -r requirements.txt
   ```
4. Run your main script:
   ```powershell
   python main.py
   ```

## Project Structure
The repository now contains a suggested structure for a dashboard + modeling project:

```
columbus-traffic-predictor/
│
├── app/                     # Interactive dashboard (Dash/Streamlit)
│   ├── __init__.py
│   ├── app.py               # Entry point for the web app
│   ├── layouts/             # UI layout definitions
│   ├── callbacks/           # Dash callbacks (interactive logic)
│   └── assets/              # CSS/images for styling
│
├── backend/                 # Data and modeling
│   ├── __init__.py
│   ├── data/                # Raw & processed data files (gitignore large files)
│   ├── models/              # Trained ML/statistical models
│   ├── preprocessing.py     # Data cleaning & feature engineering
│   ├── train_model.py       # Script for model training
│   └── predict.py           # Model inference code
│
├── notebooks/               # Jupyter Notebooks for EDA & prototyping
│   └── 01_exploration.ipynb
│
├── tests/                   # Unit tests
│   ├── test_preprocessing.py
   ├── test_train_model.py
   └── test_app.py
│
├── requirements.txt         # Python dependencies
├── README.md                # Project description & setup instructions
├── .gitignore               # Ignore large data, model binaries, venv, etc.
└── LICENSE
```

## Next Steps
Recommended next steps:

- Create a virtual environment and install dependencies from `requirements.txt`.
- Implement preprocessing, training and prediction logic in `backend/`.
- Choose a dashboard framework (Dash or Streamlit) and flesh out `app/`.
- Add real datasets to `backend/data/` and list large files in `.gitignore`.
- Run unit tests with `pytest` and expand tests under `tests/`.

Try it (powershell):
```powershell
# create venv
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
# run smoke test
C:/columbus-traffic-predictor/.venv/Scripts/python.exe main.py
```

## Training the model 

- The training script filters the dataset to ODOT District 6 (Columbus area).
- To run training with this default, execute the script:
   - PowerShell: `python backend/train_model.py`
- To override the district in code (e.g., train on all data):
   - `from backend.train_model import train_model`
   - `train_model(odot_district=None)`  # all districts
   - or `train_model(odot_district=3)`  # a specific district

   ## Pipeline overview: inputs → model → predictions

   1) Inputs (data)
   - Source CSVs: place CMS files under `backend/data/`.
   - The training entrypoint accepts a directory or glob and will concatenate files (so you can just throw the files into the data directory and the model will concatenate automatically, I may need to change this depending on naming conventions from ODOT).

   2) Preprocessing (shared by train and predict)
   - Normalize column names (lowercase, underscores), drop empty columns.
   - Coerce numeric features to numbers; impute missing values (median by default).
   - Optional schema validation to ensure required columns exist.
   - For training runs, a cleaned, concatenated snapshot is saved to:
      - `backend/data/processed/traffic_all_clean.csv`

   3) Scope filter (Columbus by default)
   - Both training and prediction default to `odot_district=6`.
   - You can override this in code (if you really want to).

   4) Model training
   - Features: maintained in code (`backend/train_model.py`), and the actually used set is stored in the model metadata.
   - Target: `car_growth_nbr`.
   - Pipeline: `SimpleImputer(strategy="median")` → `XGBRegressor` (tree_method=hist, tuned for a solid baseline).
   - Train/validation split: scikit-learn `train_test_split` (80/20) for quick metrics.
   - Artifacts written to:
      - Model bundle: `backend/models/traffic_model.pkl` (includes estimator + metadata).
      - Run log: `backend/models/training_runs.csv` (timestamp, paths, features, metrics, district).

   5) Predictions
   - Reads a CSV and re-applies preprocessing (idempotent for already-cleaned files).
   - Defaults to filter `odot_district=6` when the column is present.
   - Ensures all expected features exist; missing are added as NaN so the pipeline imputes them.
   - Writes predictions with a `predicted_car_growth_nbr` column to:
      - `backend/data/predictions/predicted_cms_car_growth.csv` 
   - If the input contains `car_growth_nbr`, it prints quick validation metrics (MAE and R²).

   How to run (PowerShell)
   ```powershell
   # Train (district 6 by default)
   C:/columbus-traffic-predictor/.venv/Scripts/python.exe -m backend.train_model

   # Predict on a CSV (district 6 by default) and print MAE/R² if target present
   C:/columbus-traffic-predictor/.venv/Scripts/python.exe -m backend.predict
   ```

   ### Common overrides
   - Train on all districts: update call to `train_model(odot_district=None)`.
   - Predict without filtering: `predict_from_csv(path, out, odot_district=None)`.
   - Use the processed snapshot for predict: `backend/data/processed/traffic_all_clean.csv`.

    ## Feature importances (from XGBoost)

    After training, the pipeline exports feature importances so you can see which inputs most influence the predictions the model makes.

    - Files written to `backend/models/`:
       - `feature_importances.csv` — sorted table of feature and importance
       - `feature_importances.png` — horizontal bar chart of the top 20 features (for more readability).
    - These importances come from the XGBoost model’s built-in importance (tree-based, typically “gain”). They are fast and helpful for a quick read but can be biased toward high-cardinality or correlated features (will look at this later).


    Interpreting importances
    - Higher value = larger contribution to reducing error in the boosted trees (basically, the feature (aka attribute) influences the traffic growth more and vice versa).
