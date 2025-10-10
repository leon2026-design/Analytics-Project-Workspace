# ============================================================
# PROJECT CONTEXT - Columbus Traffic Predictor (Backend)
#
# Goal:
#   Build a predictive model for traffic growth in Columbus, OH.
#   Data comes from ODOT/CMS traffic growth datasets. We need to pay close attention to naming conventions of these files.
#
# Current Phase (Backend focus):
#   - Ingest CSVs (starting with 2025 data).
#   - Clean and preprocess into a standardized DataFrame.
#   - Train a simple baseline regression model.
#   - Save trained models for use in the frontend.
#
# File Responsibilities:
#   preprocessing.py   → Load + clean raw CSVs, output cleaned DataFrame.
#   train_model.py     → Train baseline ML/statistical model, save as .pkl.
#   predict.py         → Load trained model and make predictions given inputs.
#
# Important Notes for VS Code Agent:
#   - Keep everything Python 3.11+ compatible.
#   - Use pandas/numpy for data handling.
#   - Code must integrate with scikit-learn (planned in train_model.py).
#   - No hardcoding of file paths → assume backend/data/ folder.
# ============================================================

 ============================================================
# DATA CONTEXT – ODOT CMS (Car Growth Rate) Dataset
#
# This dataset comes from ODOT TIMS CMS layers. Values/units:
#
# - posted_speed_nbr → mph
# - ff_speed_nbr → mph (free-flow speed)
# - section_length_nbr → miles
# - total_lanes_nbr → count
# - lane_width_nbr → feet
# - capacity_nbr → vehicles/hour (capacity per segment)
# - total_volume_nbr → vehicles/day (AADT, Annual Average Daily Traffic)
# - truck_volume_nbr → vehicles/day
# - vmt_nbr → vehicle-miles/day
# - truck_vmt_nbr → truck-miles/day
# - volume_per_lane_nbr → vehicles/lane/day
# - congestion_index_nbr → dimensionless congestion metric
# - volume_capacity_ratio_nbr → unitless ratio (demand vs capacity)
# - peak_hour_nbr → vehicles/hour (peak)
# - vht_nbr → vehicle-hours/day
# - congestion_delay_nbr / physical_delay_nbr / speed_limit_delay_nbr → vehicle-hours/day
# - delay_ratio_nbr → ratio (actual travel time vs free-flow), unitless
# - car_growth_nbr / truck_growth_nbr → annual growth rate, fraction per year (0.04 = 4%/yr)
# - los_cd → categorical Level of Service (A–F)
#
# Notes:
# - *_nbr fields are numeric measures (daily or hourly rates unless otherwise noted).
# - Growth rates are fractional (not percentages).
# - Length in miles, width in feet, speeds in mph.
#
# ============================================================