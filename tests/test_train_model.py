from backend.train_model import train

def test_train_runs():
    assert train() is None
