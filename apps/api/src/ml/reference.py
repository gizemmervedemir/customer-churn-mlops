import pandas as pd
from io import BytesIO

from src.ml.loader import read_object, get_latest_info, MODEL_PREFIX

def load_reference_df() -> tuple[pd.DataFrame, str]:
    latest = get_latest_info()
    model_version = latest["model_version"]
    prefix = latest.get("prefix", MODEL_PREFIX)

    key = f"{prefix}/{model_version}/reference.parquet"
    raw = read_object(key)
    df = pd.read_parquet(BytesIO(raw))
    return df, model_version
