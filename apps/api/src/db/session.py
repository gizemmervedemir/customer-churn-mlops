import os
from sqlmodel import SQLModel, create_engine, Session

def get_database_url() -> str:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

engine = create_engine(get_database_url(), pool_pre_ping=True)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
