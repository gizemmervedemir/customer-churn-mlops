from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class Prediction(SQLModel, table=True):
    __tablename__ = "predictions"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    model_version: str = Field(default="v0", index=True)

    # request payloadı JSON olarak saklayacağız
    features: dict = Field(sa_column=Column(JSONB), default_factory=dict)

    prediction: int = Field(nullable=False)

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column

class DriftRun(SQLModel, table=True):
    __tablename__ = "drift_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    model_version: str = Field(default="unknown", index=True)
    n_current: int = Field(default=0)

    summary: dict = Field(sa_column=Column(JSONB), default_factory=dict)   # overall
    details: dict = Field(sa_column=Column(JSONB), default_factory=dict)   # per-feature

