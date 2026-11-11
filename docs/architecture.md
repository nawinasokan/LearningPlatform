# Interview Academy architecture

The application is a modular FastAPI service backed by PostgreSQL. The frontend is a Vite React single page application. Nginx serves the compiled frontend and proxies `/api/` to FastAPI. Redis is the Celery broker and result backend.

## Request flow

```text
Browser -> Nginx -> React static files
                 -> FastAPI -> PostgreSQL
                           -> Redis/Celery worker
Coding Lab -> bounded Python subprocess
SQL Lab    -> read-only interview_sandbox database
```

Alembic owns the initial schema migration. The seed command is idempotent and creates the subject catalogue, learning content, coding exercises, SQL exercises, and diagrams. Resume extraction is deterministic and uses PDF/DOCX text extraction plus explicit keyword mappings.

## Production notes

Use a unique `SECRET_KEY`, terminate TLS before Nginx, and put code execution in a dedicated container or browser-side runtime for public deployments. The included subprocess runner is bounded for local development and interview practice.
