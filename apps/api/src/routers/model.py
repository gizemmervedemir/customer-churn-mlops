from fastapi import APIRouter, Depends

from src.core.security import verify_api_key
from src.ml.loader import reload_model

router = APIRouter(prefix="/model", tags=["model"])


@router.post("/reload")
def reload(_: str = Depends(verify_api_key)):
    _, version = reload_model()
    return {"status": "reloaded", "model_version": version}
