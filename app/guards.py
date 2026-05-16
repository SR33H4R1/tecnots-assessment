import re

from fastapi import HTTPException


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


def format_sql_for_response(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()
