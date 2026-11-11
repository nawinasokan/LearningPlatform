#!/bin/sh
# Creates the restricted, read-only role used by the SQL Lab.
# Runs once on first database initialisation (docker-entrypoint-initdb.d).
set -e
: "${SANDBOX_DB_PASSWORD:?Set SANDBOX_DB_PASSWORD in .env}"
psql -v ON_ERROR_STOP=1 -v pw="$SANDBOX_DB_PASSWORD" --username "$POSTGRES_USER" --dbname interview_sandbox <<'SQL'
SELECT format('CREATE ROLE sandbox_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 10 PASSWORD %L', :'pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sandbox_reader')
\gexec
ALTER ROLE sandbox_reader SET statement_timeout = '5s';
ALTER ROLE sandbox_reader SET search_path = sandbox;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT ON DATABASE interview_sandbox FROM PUBLIC;
GRANT CONNECT ON DATABASE interview_sandbox TO sandbox_reader;
GRANT USAGE ON SCHEMA sandbox TO sandbox_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA sandbox TO sandbox_reader;
SQL
