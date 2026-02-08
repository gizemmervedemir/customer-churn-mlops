from fastapi import FastAPI
from src.routers.health import router as health_router
from src.routers.predict import router as predict_router
from src.db.session import init_db
from src.routers.drift import router as drift_router
from src.routers.model import router as model_router


app = FastAPI(title="Customer Churn MLOps API", version="0.1.0")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(health_router)
app.include_router(predict_router)
app.include_router(drift_router)
app.include_router(model_router)
