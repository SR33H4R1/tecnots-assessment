# Natural Language PostgreSQL Query API

A small FastAPI application that turns natural language questions into read-only PostgreSQL queries using the NIA API. It introspects the live database schema, generates SQL, runs the query safely, and returns JSON results through both an API and a lightweight web UI.

## Demo

![Demo UI](screenshots/demo.png)

## Features

- Natural language to SQL conversion
- Dynamic PostgreSQL schema introspection
- Read-only SQL execution
- Shared SQLAlchemy connection pool
- Swagger/OpenAPI testing at `/docs`
- Lightweight browser UI

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

Open the web UI:

```text
http://localhost:8000/
```

Open Swagger UI:

```text
http://localhost:8000/docs
```

## Endpoints

### `GET /schema`

Returns the current PostgreSQL schema metadata from `information_schema.columns`.

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

## Safety Note

Generated SQL is limited to read-only `SELECT` queries. The app blocks unsafe query patterns, applies query timeout protection, and limits result rows to keep responses practical.

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- OpenAI-compatible NIA API client
- Vanilla HTML/CSS/JavaScript
