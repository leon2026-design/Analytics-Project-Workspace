import os
import pandas as pd

from backend.predict import predict_from_dataframe
from backend.preprocessing import load_all_data, recompute_2026_time_features


def main() -> None:
	data_dir = "backend/data"
	predictions_dir = os.path.join(data_dir, "predictions")

	# Load the same aggregated, preprocessed dataset used for training
	df_all = load_all_data(data_dir)

	# Restrict to 2025 District 6 slice as the baseline
	df_2025_d6 = df_all[(df_all.get("year") == 2025) & (df_all.get("odot_district") == 6)].copy()
	if df_2025_d6.empty:
		raise RuntimeError("No 2025 District 6 rows found in aggregated dataset.")

	# Create a 2026 copy of the 2025 District 6 baseline
	df_2026_d6 = df_2025_d6.copy()
	df_2026_d6["year"] = 2026

	# Recompute year_norm/year_poly2 for 2026 only, using
	# the historical training-era year range from df_all.
	df_2026_d6 = recompute_2026_time_features(df_all, df_2026_d6)

	# Save 2026 input slice for record
	cms_2026_path = os.path.join(data_dir, "CMS_2026.csv")
	df_2026_d6.to_csv(cms_2026_path, index=False)

	# Predict 2026 using the same feature schema as training
	os.makedirs(predictions_dir, exist_ok=True)
	result_df = predict_from_dataframe(df_2026_d6)
	out_path = os.path.join(predictions_dir, "predicted_cms_2026.csv")
	result_df.to_csv(out_path, index=False)
	print(f"2026 predictions saved to {out_path}")


if __name__ == "__main__":
	main()
