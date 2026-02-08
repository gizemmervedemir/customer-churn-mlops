import os
import json
from src.ml.loader import read_object, get_latest_info, MODEL_PREFIX

def get_feature_schema() -> dict:
    latest = get_latest_info()
    model_version = latest["model_version"]
    prefix = latest.get("prefix", MODEL_PREFIX)

    metrics_key = f"{prefix}/{model_version}/metrics.json"
    raw = read_object(metrics_key)
    return json.loads(raw.decode("utf-8"))
