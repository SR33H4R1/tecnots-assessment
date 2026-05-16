import logging
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.database import execute_select, get_engine
from app.guards import format_sql_for_response
from app.llm import generate_sql
from app.schema import introspect_schema


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
MAX_QUESTION_LENGTH = 500

app = FastAPI(
    title="Natural Language PostgreSQL Query API",
    description="Runtime PostgreSQL schema introspection with NIA-generated safe SELECT queries.",
    version="0.1.0",
)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH, examples=["Show the first 10 customers"])


class QueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int


@app.on_event("startup")
def log_startup() -> None:
    logger.info("Natural Language PostgreSQL Query API started")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "index.html")


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
    return QueryResponse(sql=format_sql_for_response(generated_sql), rows=rows, row_count=len(rows))
