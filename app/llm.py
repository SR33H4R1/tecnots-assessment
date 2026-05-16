import json
import os
import re
from typing import Any

from fastapi import HTTPException
from openai import OpenAI


NIA_API_KEY = os.getenv("NIA_API_KEY")
NIA_BASE_URL = "https://nia.naslabs.ai/api/v1"
NIA_MODEL = "nia-a-1.0"


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
