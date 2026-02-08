from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from src.core.security import verify_api_key
from src.db.session import get_session
from src.db.models import Prediction
from src.ml.loader import load_model_cached
from src.ml.schema import get_feature_schema
from src.ml.predict import sanitize_features, to_dataframe

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    # Esnek: UI schema’dan kolonları alıp buraya dict basacak
    features: dict


@router.get("/schema")
def schema(_: str = Depends(verify_api_key)):
    s = get_feature_schema()
    return {
        "model_version": s.get("model_version"),
        "num_cols": s.get("num_cols", []),
        "cat_cols": s.get("cat_cols", []),
    }


@router.post("")
def predict(
    payload: PredictRequest,
    _: str = Depends(verify_api_key),
    session: Session = Depends(get_session),
):
    # 1) model + version
    pipe, model_version = load_model_cached()

    # 2) schema
    schema_info = get_feature_schema()
    num_cols = schema_info.get("num_cols", [])
    cat_cols = schema_info.get("cat_cols", [])

    # 3) sanitize payload (drop unknown cols, cast numerics, fill missing)
    clean = sanitize_features(payload.features, num_cols=num_cols, cat_cols=cat_cols)

    # 4) dataframe -> predict
    X = to_dataframe(clean)
    proba = float(pipe.predict_proba(X)[:, 1][0])
    pred = 1 if proba >= 0.5 else 0

    # 5) log to DB (store clean features!)
    row = Prediction(
        model_version=model_version,
        features=clean,
        prediction=pred,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    return {
        "prediction": pred,
        "probability": proba,
        "model_version": model_version,
        "id": row.id,
    }


@router.get("/latest")
def latest(
    _: str = Depends(verify_api_key),
    session: Session = Depends(get_session),
):
    q = select(Prediction).order_by(Prediction.id.desc()).limit(5)
    rows = session.exec(q).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "model_version": r.model_version,
            "features": r.features,
            "prediction": r.prediction,
        }
        for r in rows
    ]
