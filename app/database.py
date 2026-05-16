import os
import logging
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.guards import validate_safe_select


load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_ROWS = 500


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
                connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                result = connection.execute(text(sql))
                rows = result.mappings().fetchmany(MAX_ROWS + 1)
                return [dict(row) for row in rows[:MAX_ROWS]]
    except SQLAlchemyError as exc:
        logger.exception("Database query execution failed")
        raise HTTPException(status_code=503, detail="Database query execution failed") from exc
