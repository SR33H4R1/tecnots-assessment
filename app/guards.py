import logging
import re

from fastapi import HTTPException


logger = logging.getLogger(__name__)

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

DANGEROUS_FUNCTIONS = {
    "pg_read_file",
    "pg_read_binary_file",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "lo_import",
    "lo_export",
    "lo_get",
    "lo_put",
    "dblink",
    "dblink_exec",
}


def remove_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)


def validate_safe_select(sql: str) -> None:
    clean_sql = remove_sql_comments(sql).strip()
    if not clean_sql:
        logger.warning("Blocked empty generated SQL")
        raise HTTPException(status_code=400, detail="Generated SQL is empty")

    if ";" in clean_sql:
        logger.warning("Blocked SQL containing semicolon")
        raise HTTPException(status_code=400, detail="Only one SQL statement is allowed")

    if not re.match(r"^\s*SELECT\b", clean_sql, flags=re.IGNORECASE):
        logger.warning("Blocked non-SELECT SQL")
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    tokens = set(re.findall(r"\b[A-Z_]+\b", clean_sql.upper()))
    blocked = sorted(tokens.intersection(DANGEROUS_KEYWORDS))
    if blocked:
        logger.warning("Blocked SQL with forbidden keyword(s): %s", ", ".join(blocked))
        raise HTTPException(
            status_code=400,
            detail=f"Unsafe SQL blocked. Forbidden keyword(s): {', '.join(blocked)}",
        )

    lower_sql = clean_sql.lower()
    blocked_functions = sorted(
        function
        for function in DANGEROUS_FUNCTIONS
        if re.search(rf"\b{re.escape(function)}\s*\(", lower_sql)
    )
    if blocked_functions:
        logger.warning("Blocked SQL with forbidden function(s): %s", ", ".join(blocked_functions))
        raise HTTPException(
            status_code=400,
            detail=f"Unsafe SQL blocked. Forbidden function(s): {', '.join(blocked_functions)}",
        )


def format_sql_for_response(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()
