from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
import pandas as pd

from src.core.security import verify_api_key
from src.db.session import get_session
from src.db.models import Prediction, DriftRun
from src.ml.reference import load_reference_df
from src.ml.schema import get_feature_schema
from src.ml.drift import compute_drift

router = APIRouter(prefix="/drift", tags=["drift"])


@router.get("/check")
def drift_check(
    _: str = Depends(verify_api_key),
    session: Session = Depends(get_session),
    n: int = Query(200, ge=20, le=2000),
):
    # 1) reference from MinIO
    reference_df, model_version = load_reference_df()

    # 2) schema
    schema = get_feature_schema()
    num_cols = schema.get("num_cols", [])
    cat_cols = schema.get("cat_cols", [])

    # 3) current from DB (last n)
    q = select(Prediction).order_by(Prediction.id.desc()).limit(n)
    rows = session.exec(q).all()
    if len(rows) < 20:
        return {"detail": "Not enough predictions yet. Call /predict at least 20 times.", "n_current": len(rows)}

    current_df = pd.DataFrame([r.features for r in rows])

    # ensure columns exist
    for c in num_cols:
        if c not in current_df.columns:
            current_df[c] = 0.0
    for c in cat_cols:
        if c not in current_df.columns:
            current_df[c] = ""

    # 4) compute drift
    summary, details = compute_drift(
        reference=reference_df,
        current=current_df,
        num_cols=num_cols,
        cat_cols=cat_cols,
        psi_threshold=0.2,
        cat_threshold=0.2,
    )

    # 5) log drift run
    run = DriftRun(
        model_version=model_version,
        n_current=len(rows),
        summary=summary,
        details=details,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    return {"id": run.id, "model_version": model_version, "summary": summary, "details": details}
