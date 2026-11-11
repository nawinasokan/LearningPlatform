# Interview Academy

A personalized learning and interview preparation platform for Python backend development. The stack uses FastAPI, PostgreSQL, Redis, Celery, React, Vite, and Nginx.

## Run with Docker Compose

1. Copy `.env.example` to `.env` and change `SECRET_KEY` before exposing the service beyond localhost.
2. Start the stack with `docker compose up --build`.
3. Open [http://localhost](http://localhost). FastAPI docs are at [http://localhost/docs](http://localhost/docs).

PostgreSQL defaults are `interview_user` / `interview_pass` / `interview_academy`. The SQL sandbox is initialized separately by `backend/scripts/init_sandbox.sql`.

## Local development

Start PostgreSQL and Redis first, then set host-accessible URLs in `.env`. From `backend/`, install dependencies and run:

```sh
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload
```

Run the backend checks with `pytest -q`. The suite covers route registration and the bounded coding runner.

From `frontend/`, run `npm install && npm run dev`. Vite's dev server can be configured with `VITE_API_URL` if the API is not proxied at `/api/v1`.

## Current application areas

- JWT registration, login, refresh, and authenticated profile
- Resume upload and deterministic PDF/DOCX extraction
- Subject, topic, question, coding, and SQL practice APIs
- Diagrams, bookmarks, analytics, and daily revision APIs
- Seeded curriculum content and a responsive dashboard / learning-path UI

Python coding exercises execute in short lived subprocesses with a timeout. This is intended for local development; do not expose code execution to untrusted users on a public deployment without stronger OS/container isolation.
