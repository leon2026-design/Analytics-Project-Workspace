import pandas as pd
from backend.core.preprocessing import clean

def test_clean_noop():
    df = pd.DataFrame({"a": [1,2,3]})
    out = clean(df)
    assert out.equals(df)
