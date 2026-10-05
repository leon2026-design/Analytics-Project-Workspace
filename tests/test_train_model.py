import backend.core.train_model as train_module


def test_train_delegates_to_train_model(monkeypatch):
    expected = object()
    captured = {}

    def fake_train_model(data_path, model_path, odot_district):
        captured.update(
            data_path=data_path,
            model_path=model_path,
            odot_district=odot_district,
        )
        return expected

    monkeypatch.setattr(train_module, "train_model", fake_train_model)

    assert train_module.train("input.csv", "model.pkl", odot_district=None) is expected
    assert captured == {
        "data_path": "input.csv",
        "model_path": "model.pkl",
        "odot_district": None,
    }
