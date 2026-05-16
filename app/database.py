import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.guards import validate_safe_select


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return database_url


engine: Engine | None = (
    create_engine(
        normalize_database_url(DATABASE_URL),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    if DATABASE_URL
    else None
)


def get_engine() -> Engine:
    if engine is None:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return engine


def execute_select(engine: Engine, sql: str) -> list[dict[str, Any]]:
    validate_safe_select(sql)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                result = connection.execute(text(sql))
                return [dict(row) for row in result.mappings().all()]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database query execution failed: {exc}") from exc
