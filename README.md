# Natural Language PostgreSQL Query API

FastAPI application that accepts natural language questions, introspects a live PostgreSQL schema at runtime, generates SQL using the NIA API, validates query safety, executes read-only SELECT queries, and returns JSON results.

## Demo

![Demo UI](screenshots/demo.png)

## Setup

1. Create `.env` from `.env.example`.
2. Set:
   - `DATABASE_URL`
   - `NIA_API_KEY`
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open the demo UI:

```text
http://localhost:8000/
```

Open Swagger UI:

```text
http://localhost:8000/docs
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
