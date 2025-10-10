import os
import pandas as pd
from backend.preprocessing import clean_data, coerce_numeric, validate_schema, save_processed


def test_fill_strategies(tmp_path):
    df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, None]})
    out_zero = clean_data(df, fill_strategy="zero")
    assert out_zero["a"].tolist() == [1, 0, 3]
    out_median = clean_data(df, fill_strategy="median")
    assert out_median["a"].tolist() == [1, 2.0, 3]


def test_coerce_numeric():
    df = pd.DataFrame({"num_str": ["1", "2", "x"], "keep": ["a", "b", "c"]})
    out = coerce_numeric(df, columns=["num_str"])
    assert pd.api.types.is_numeric_dtype(out["num_str"]) or out["num_str"].isnull().any()


def test_validate_schema():
    df = pd.DataFrame({"col_one": [1], "col_two": [2]})
    # should not raise
    validate_schema(df, required_columns=["col one", "col two"])
    try:
        validate_schema(df, required_columns=["col three"])
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_save_processed(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    out = tmp_path / "processed" / "out.csv"
    save_processed(df, str(out))
    assert out.exists()
    loaded = pd.read_csv(out)
    assert loaded.shape == (2, 1)
