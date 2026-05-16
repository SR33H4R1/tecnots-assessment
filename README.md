# Natural Language PostgreSQL Query API

FastAPI MVP that accepts natural language questions, introspects a live PostgreSQL schema at runtime, asks the NIA API to generate SQL, blocks unsafe SQL, executes safe read-only `SELECT` queries, and returns JSON results.

## Setup

1. Create `.env` from `.env.example`.
2. Set:
   - `DATABASE_URL`
   - `NIA_API_KEY`
3. Install dependencies:

```powershell
& "C:\Users\Sreehari\tecdots-assessment\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Run

```powershell
& "C:\Users\Sreehari\tecdots-assessment\.venv\Scripts\python.exe" -m uvicorn main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### `GET /schema`

Dynamically reads PostgreSQL schema metadata from `information_schema.columns`.

### `POST /query`

Request:

```json
{
  "question": "Show the first 10 records"
}
```

Response:

```json
{
  "sql": "SELECT ...",
  "rows": [],
  "row_count": 0
}
```

## Guardrails

Only single-statement `SELECT` queries are allowed.

Blocked keywords:

- `DROP`
- `DELETE`
- `UPDATE`
- `INSERT`
- `ALTER`
- `TRUNCATE`
- `CREATE`
- `GRANT`
- `REVOKE`

No table or column names are hardcoded. Schema is introspected on each request so database changes are picked up at runtime.
