import os
import json
import joblib
import boto3
from io import BytesIO
from functools import lru_cache
from typing import Tuple, Any

# ======================
# Environment
# ======================

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mlops-artifacts")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")

MODEL_PREFIX = os.getenv("MODEL_PREFIX", "churn_model")
LATEST_KEY = f"{MODEL_PREFIX}/latest.json"


# ======================
# MinIO / S3 client
# ======================

def s3_client():
    """
    Creates a MinIO-compatible S3 client.
    """
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def read_object(key: str) -> bytes:
    """
    Reads an object from MinIO and returns raw bytes.
    """
    s3 = s3_client()
    obj = s3.get_object(Bucket=MINIO_BUCKET, Key=key)
    return obj["Body"].read()


# ======================
# Model metadata
# ======================

def get_latest_info() -> dict:
    """
    Reads latest.json and returns metadata:
    {
        "model_version": "...",
        "prefix": "churn_model"
    }
    """
    raw = read_object(LATEST_KEY)
    return json.loads(raw.decode("utf-8"))


# ======================
# Model loading
# ======================

@lru_cache(maxsize=1)
def load_model_cached() -> Tuple[Any, str]:
    """
    Loads the latest model pipeline from MinIO.

    Returns:
        (pipeline, model_version)

    This function is cached in-memory.
    To force reload, call reload_model().
    """
    latest = get_latest_info()

    model_version = latest["model_version"]
    prefix = latest.get("prefix", MODEL_PREFIX)

    model_key = f"{prefix}/{model_version}/model.joblib"
    model_bytes = read_object(model_key)

    pipe = joblib.load(BytesIO(model_bytes))

    return pipe, model_version


def reload_model() -> Tuple[Any, str]:
    """
    Clears the in-memory cache and reloads the latest model.

    Used by /model/reload endpoint.
    """
    try:
        load_model_cached.cache_clear()
    except Exception:
        # cache may not exist yet
        pass

    return load_model_cached()
