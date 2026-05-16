from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def introspect_schema(engine: Engine) -> list[dict[str, Any]]:
    schema_sql = text(
        """
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type,
            is_nullable,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_schema, table_name, ordinal_position
        """
    )

    tables: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        with engine.connect() as connection:
            rows = connection.execute(schema_sql).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database schema introspection failed: {exc}") from exc

    for row in rows:
        key = (row["table_schema"], row["table_name"])
        if key not in tables:
            tables[key] = {
                "schema": row["table_schema"],
                "table": row["table_name"],
                "columns": [],
            }
        tables[key]["columns"].append(
            {
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
            }
        )

    return list(tables.values())
