import json
import re
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

import os


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
NIA_API_KEY = os.getenv("NIA_API_KEY")
NIA_BASE_URL = "https://nia.naslabs.ai/api/v1"
NIA_MODEL = "nia-a-1.0"

DANGEROUS_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
}

app = FastAPI(
    title="Natural Language PostgreSQL Query API",
    description="Runtime PostgreSQL schema introspection with NIA-generated safe SELECT queries.",
    version="0.1.0",
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["Show the first 10 customers"])


class QueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int


def get_database_url() -> str:
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return DATABASE_URL


def get_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True)


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


def format_schema_for_prompt(schema: list[dict[str, Any]]) -> str:
    return json.dumps(schema, indent=2)


def get_nia_client() -> OpenAI:
    if not NIA_API_KEY:
        raise HTTPException(status_code=500, detail="NIA_API_KEY is not configured")
    return OpenAI(api_key=NIA_API_KEY, base_url=NIA_BASE_URL)


def extract_sql(content: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    sql = fenced.group(1) if fenced else content
    sql = sql.strip()
    if sql.endswith(";"):
        sql = sql[:-1].strip()
    return sql


def generate_sql(question: str, schema: list[dict[str, Any]]) -> str:
    client = get_nia_client()
    schema_text = format_schema_for_prompt(schema)
    response = client.chat.completions.create(
        model=NIA_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate PostgreSQL SQL from natural language. "
                    "Use only the provided schema. "
                    "Return exactly one read-only SELECT query and no explanation. "
                    "Do not invent tables or columns. "
                    "Do not use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, or REVOKE."
                ),
            },
            {
                "role": "user",
                "content": f"Schema:\n{schema_text}\n\nQuestion:\n{question}",
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return extract_sql(content)


def remove_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)


def validate_safe_select(sql: str) -> None:
    clean_sql = remove_sql_comments(sql).strip()
    if not clean_sql:
        raise HTTPException(status_code=400, detail="Generated SQL is empty")

    if ";" in clean_sql:
        raise HTTPException(status_code=400, detail="Only one SQL statement is allowed")

    if not re.match(r"^\s*SELECT\b", clean_sql, flags=re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    tokens = set(re.findall(r"\b[A-Z_]+\b", clean_sql.upper()))
    blocked = sorted(tokens.intersection(DANGEROUS_KEYWORDS))
    if blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Unsafe SQL blocked. Forbidden keyword(s): {', '.join(blocked)}",
        )


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


@app.get("/schema")
def schema() -> dict[str, Any]:
    engine = get_engine()
    return {"tables": introspect_schema(engine)}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    engine = get_engine()
    schema_metadata = introspect_schema(engine)
    generated_sql = generate_sql(request.question, schema_metadata)
    rows = execute_select(engine, generated_sql)
    return QueryResponse(sql=generated_sql, rows=rows, row_count=len(rows))
