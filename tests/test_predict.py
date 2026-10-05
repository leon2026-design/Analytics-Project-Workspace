import joblib
import pandas as pd

from backend.core.predict import predict_from_csv


class FeatureSumModel:
    def predict(self, frame):
        return frame["total_volume_nbr"] + frame["year"]


def test_predict_from_csv_uses_supplied_input_file(tmp_path):
    input_csv = tmp_path / "traffic_2026.csv"
    output_csv = tmp_path / "predictions.csv"
    model_path = tmp_path / "model.pkl"
    pd.DataFrame(
        {
            "district": [6, 7],
            "totalvolume": [10, 99],
        }
    ).to_csv(input_csv, index=False)
    joblib.dump(
        {
            "model": FeatureSumModel(),
            "meta": {"features": ["total_volume_nbr", "year"]},
        },
        model_path,
    )

    result = predict_from_csv(
        str(input_csv),
        str(output_csv),
        str(model_path),
        odot_district=6,
    )

    assert result["total_volume_nbr"].tolist() == [10]
    assert result["year"].tolist() == [2026]
    assert result["predicted_car_growth_nbr"].tolist() == [2036]
    assert output_csv.exists()
