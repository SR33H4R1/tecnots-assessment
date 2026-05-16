import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.guards import validate_safe_select


DATABASE_URL = os.getenv("DATABASE_URL")


def get_database_url() -> str:
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    if DATABASE_URL.startswith("postgresql+asyncpg://"):
        return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return DATABASE_URL


def get_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True)


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
