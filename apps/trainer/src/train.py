import os
import json
import joblib
import boto3
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

DATA_PATH = os.getenv("DATA_PATH", "/app/data/raw/telco_churn.csv")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mlops-artifacts")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")

MODEL_PREFIX = os.getenv("MODEL_PREFIX", "churn_model")
MODEL_VERSION = os.getenv("MODEL_VERSION") or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M%S")


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def upload_bytes(key: str, content: bytes, content_type: str = "application/octet-stream"):
    s3 = s3_client()
    s3.put_object(Bucket=MINIO_BUCKET, Key=key, Body=content, ContentType=content_type)


def main():
    df = pd.read_csv(DATA_PATH)

    # Target normalize
    # Dataset bazen "Churn" -> "Yes/No"
    df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0})

    # TotalCharges bazen string + boş olabilir
    if "TotalCharges" in df.columns:
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
        df["TotalCharges"] = df["TotalCharges"].fillna(0)

    # customerID'i drop
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    y = df["Churn"].astype(int)
    X = df.drop(columns=["Churn"])

    cat_cols = X.select_dtypes(include=["object"]).columns.tolist()
    num_cols = [c for c in X.columns if c not in cat_cols]

    pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", StandardScaler())]), num_cols),
            ("cat", Pipeline([("oh", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
        ]
    )

    model = LogisticRegression(max_iter=500)

    pipe = Pipeline([
        ("preprocess", pre),
        ("model", model),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, proba))

    # reference dataset: train'in bir kısmını sakla (drift için)
    reference = X_train.sample(n=min(500, len(X_train)), random_state=42).copy()

    # artifacts
    model_bytes = BytesIO()
    joblib.dump(pipe, model_bytes)
    model_bytes.seek(0)

    metrics = {
        "roc_auc": auc,
        "model_version": MODEL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "n_features": int(X.shape[1]),
        "cat_cols": cat_cols,
        "num_cols": num_cols,
    }

    # Upload paths
    base = f"{MODEL_PREFIX}/{MODEL_VERSION}"
    upload_bytes(f"{base}/model.joblib", model_bytes.read(), "application/octet-stream")
    upload_bytes(f"{base}/metrics.json", json.dumps(metrics, indent=2).encode("utf-8"), "application/json")

    # reference parquet
    ref_buf = BytesIO()
    reference.to_parquet(ref_buf, index=False)
    ref_buf.seek(0)
    upload_bytes(f"{base}/reference.parquet", ref_buf.read(), "application/octet-stream")

    # Also upload a pointer to "latest"
    latest = {"model_version": MODEL_VERSION, "prefix": MODEL_PREFIX}
    upload_bytes(f"{MODEL_PREFIX}/latest.json", json.dumps(latest).encode("utf-8"), "application/json")

    print("✅ Training finished")
    print("Model version:", MODEL_VERSION)
    print("AUC:", auc)
    print("Uploaded to:", f"s3://{MINIO_BUCKET}/{base}/")


if __name__ == "__main__":
    main()
