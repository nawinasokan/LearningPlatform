# Interview Academy — Project Implementation Audit

- **Audit date:** 2026-11-11
- **Method:** Code inspection of every backend/frontend file, direct SQL counts against the running Docker database, and live HTTP calls against `localhost:8000/api/v1` (registered a throwaway user `audit@example.com`, uploaded a generated DOCX, exercised every route in the master plan's API list). `pytest` was run in `backend/`.
- **Scoring rule:** a feature counts as *Completed* only if I observed it working end-to-end in this audit. Percentages are my judgement against the master prompt, not tool output. Sections 6–7 are updated as fixes land; only items marked **VERIFIED** were re-tested after the fix.

---

## 1. Summary

| | |
|---|---|
| **Overall completion (honest estimate)** | **≈ 40 %** (after the security/resume fixes below) |
| Backend API surface | ≈ 80 % present, ≈ 70 % working |
| Database schema | ≈ 90 % (all 25 tables exist) |
| Seed content (quality, not row count) | ≈ 10 % |
| Frontend vs. spec | ≈ 25 % |
| Security | **2 critical holes** (code sandbox, SQL sandbox) |
| Automated tests | 3 trivial tests |

**Headline findings**

1. **The question bank is mostly filler.** 920 rows exist and match the target counts, but only **63** are real questions. The other **857** are generated placeholders such as *"Python interview practice 17: explain the concept and a production tradeoff."* with answers like *"Start with the purpose and a small example from FastAPI."* (`seed.py::_ensure_question_targets`). Same pattern for coding problems (45 of 50 are `Python practice problem N`) and SQL problems (35 of 40). The target counts were met by padding, which violates "avoid duplicates / no placeholder data".
2. **Critical: SQL Lab can read server files.** `select pg_read_file('/etc/passwd')` returned the file contents; the sandbox connects as the superuser role `interview_user`, and the keyword filter is bypassable.
3. **Critical: Python sandbox leaks secrets.** Submitted code printed the backend's `SECRET_KEY` (full `os.environ` is passed to the child) and can read container files and use the network. Only rlimits are applied.
4. **Resume "extraction" is partly fake.** `resume_parser.py` always injects hardcoded facts/projects for one specific person regardless of the uploaded file (a generic test DOCX produced "Built backend systems handling 150M+ rows…" facts that were not in the document).
5. **Frontend does not follow the spec.** One 26 KB `main.jsx`; no Bootstrap 5, no Monaco, no Mermaid rendering (diagrams show raw source in a `<pre>`), flat 10-item sidebar instead of 21 grouped/collapsible sections.
6. **Compliance check passed:** no Gemini API integration, no AI mock interview, no interview validation module. "Gemini" appears only as project learning text (resume project tech lists / answers), which the plan permits.

---

## 2. Module-wise completion

| # | Module | % | Status |
|---|---|---|---|
| 1 | Authentication (register/login/me/refresh, JWT, argon2) | 80 | Works; no rate limiting; refresh tokens not revocable |
| 2 | Resume management | 35 | Upload + skill→subject mapping work; extraction fake; no `PATCH /resumes/{id}`; no skill/project/experience editing UI; no version-history UI |
| 3 | Learning content structure (Subject→Topic→Subtopic→Concept) | 25 | 13 subjects/26 topics; 0 subtopics; 0 prerequisites; only 8 of 26 topics have `learning_content` |
| 4 | Question bank + explanation modes | 20 | 3 modes work end-to-end; 63 real / 857 filler questions; 0 tags |
| 5 | Python coding lab | 30 | Run/submit/history work; **sandbox insecure**; 5 real problems; textarea not Monaco |
| 6 | SQL practice lab | 30 | Execute works; **sandbox insecure**; 5 real problems; no expected-result validation |
| 7 | Visual learning | 20 | 6 of 17 diagrams; Mermaid not rendered; no zoom/fullscreen/copy/SVG export |
| 8 | Project deep dive | 40 | 3 projects + 11 real questions; `GET /projects/{id}` 404s for the IDs the list returns |
| 9 | Progress, analytics, revision | 55 | Dashboard uses real DB values and Recharts; revision endpoints work; no flashcards; daily plan/recommendation unverified |
| 10 | Bookmarks | 85 | Create/list works |
| 11 | Navigation / layout | 25 | 10 flat links, not grouped/collapsible |
| 12 | Backend architecture | 45 | Logic lives in routers; `repositories/` empty; 2 of 8 services; no centralized exception handler |
| 13 | Database & migrations | 60 | Models good; migration `0001` is `Base.metadata.create_all` (not a real versioned migration) |
| 14 | Testing | 10 | 3 tests (route registration, runner) |
| 15 | Docs | 15 | Only `architecture.md`; 6 required docs missing |
| 16 | Docker / deployment | 75 | Stack runs (postgres, redis, backend, celery, frontend, nginx) |

---

## 3. Completed (observed working)

- Register, login, `/auth/me`, `/auth/refresh` (HTTP 200s).
- `GET /subjects`, `/subjects/{id}/topics`, `/topics/{id}`, `/topics/{id}/questions`, `/questions`, `/questions/{id}`, `/questions/{id}/answers`, `POST /questions/{id}/complete`.
- Bookmarks: create + list.
- Coding: list problems, run, submit, submissions history.
- SQL: list problems, execute (SELECT).
- Resume upload of DOCX; non-PDF/DOCX rejected (400).
- Resume fact verification toggle (`PATCH /resumes/{id}/facts/{fact_id}`).
- Analytics: dashboard, subjects, weak-topics, history; `GET /revision/today`; `GET /diagrams`.
- Pytest: 3 passed.

## 4. Partially completed

- Resume management (see §2).
- Learning content: model supports all 14 concept fields; data exists for 8 topics only.
- Visual learning: data model + API + 6 diagrams; no rendering/tools.
- Question bank: structure works; content mostly placeholder.
- Coding lab: 5 real problems with test cases; 45 filler.
- SQL lab: 5 real problems; no solution/result checking.
- Revision: `RevisionSchedule` + SM-2-style fields; flashcards table empty.
- Frontend pages: all routes exist but as compact single-file components.

## 5. Missing

- Bootstrap 5 design system, Monaco editor, Mermaid renderer + diagram tools.
- Grouped collapsible sidebar with 21 sections; dedicated Academy pages (Python/Django/FastAPI/Flask/SQL/…).
- Subtopics, topic prerequisites, tags (`question_tags`, mappings), flashcards data.
- 11 of 17 required diagrams.
- Real content for ~857 questions, 45 coding problems, 35 SQL problems, 18 topics' learning content.
- `PATCH /resumes/{id}`; resume skill/project/experience/achievement editing; version-history UI.
- Services `content_service`, `progress_service`, `recommendation_service`, `revision_service`, `sql_service`, `diagram_service`; repositories layer.
- Centralized exception handling; request logging.
- Alembic migration that is not `create_all`.
- Docs: PROJECT_PLAN, DATABASE_SCHEMA, API_DOCUMENTATION, IMPLEMENTATION_STATUS, TESTING_REPORT.
- Meaningful automated tests (API, parser, sandbox, recommendation, revision).

## 6. Broken

| ID | Item | Evidence | Sev |
|---|---|---|---|
| B1 | SQL sandbox reads server files / is superuser | `select pg_read_file('/etc/passwd')` → file contents; `current_user = interview_user` | Critical |
| B2 | Python sandbox leaks env + FS | submitted code printed `SECRET_KEY` | Critical |
| B3 | `GET /projects/{id}` and `/projects/{id}/questions` → 404 | list returns UUID `id`, detail looks up by slug only | High |
| B4 | Resume parser injects hardcoded facts/projects | generic DOCX → "150M+ rows" facts | High |
| B5 | `PATCH /resumes/{id}` → 405 | spec route missing | Medium |
| B6 | `GET /questions?search=` silently ignored | returns unfiltered results | Low |
| B7 | Mermaid diagrams render as raw text | `<pre className="diagram-source">` | Medium |

## 7. Bugs and technical issues

- Resume upload: unsanitised `file.filename` in path (path traversal risk), no size limit enforced despite `MAX_UPLOAD_SIZE`, extension check case-sensitive.
- SQL guard (original): substring keyword match that falsely rejected valid queries containing words like `CREATE` in text/identifiers, accepted multi-statement input, and concatenated `SET ...;` with the learner's query.
- Python runner: stdin injected via `repr()` into source; `from __future__` imports in user code would break; no network/FS isolation.
- `get_subjects` / `get_topics` run N+1 queries per row.
- `SECRET_KEY` default in config is empty; container showed a placeholder secret value.
- Duplicate `httpx` pin in requirements; `python-jose` and `pyjwt` both listed.
- Class-based pydantic `Config` deprecated.
- `venv/` directory exists inside `backend/` (should be gitignored; confirm).

## 8. Database and API issues

- Migration is `create_all`, so schema changes cannot be versioned.
- `subtopics`, `topic_prerequisites`, `question_tags`, `question_tag_mappings`, `flashcards` have 0 rows (recommendation by prerequisites cannot work).
- `/projects` returns topics rather than a project entity; fine as modelling, but id/slug contract was inconsistent (B3).
- No uniqueness protection on question text → filler could duplicate if re-seeded with a different scheme.
- Real counts vs. targets: all subject targets met by padding; real counts: Python 16, Django 10, FastAPI 5, Flask 2, SQL 7, DB-eng 2, Backend 2, Celery/Redis 4, Docker/Linux 2, AWS/GCP 2, JS/React 2, System design 2, Projects 7.

## 9. Testing results (this audit)

| Test | Result |
|---|---|
| `pytest` in `backend/` | 3 passed |
| 30+ live API calls (see §3) | all returned expected status except B3, B5, and the `resumes/latest` 404 for a user with no resume (correct behaviour) |
| SQL injection / file read | **FAILED** (B1) |
| Python sandbox isolation | **FAILED** (B2) |
| Frontend | not browser-tested in this audit pass (static review only) |

Cleanup note: the audit created user `audit@example.com` and one resume in the dev database; it is removed at the end of the fix pass (see §10).

## 10. Prioritized pending tasks / roadmap

**P0 — security (do first)**
1. Isolate SQL sandbox: dedicated non-superuser read-only role, single-statement only, parser-based guard. 
2. Isolate Python runner: scrubbed environment, `python -I`, empty temp cwd, no network where possible, tighter rlimits.

**P1 — broken functionality**
3. Fix project id/slug lookup (B3).
4. Remove hardcoded resume facts/projects; real extraction only (B4); add `PATCH /resumes/{id}`; sanitise filename + enforce size cap (B5, §7).
5. Wire `search` on `/questions` (B6).

**P2 — content integrity**
6. Stop seeding filler: delete padding generators; keep real content only; report real counts honestly.
7. Author real content per priority (Python → Django → FastAPI → PostgreSQL → F1) — multi-session effort.

**P3 — frontend to spec**
8. Bootstrap 5 + grouped collapsible sidebar; split `main.jsx` into the spec's folder structure.
9. Mermaid rendering with fullscreen/zoom/copy/SVG export; Monaco editor.
10. Resume editing UI + skill→subject dashboard.

**P4 — engineering quality**
11. Real Alembic migrations; services/repositories split; centralized exceptions; tests; remaining docs.

---

## 11. Fix log (updated as work proceeds)

| Date | Item | Status |
|---|---|---|
| 2026-11-11 | **B1** SQL sandbox: new non-superuser `sandbox_reader` role (SELECT on `sandbox` schema only, no `public`, 5 s timeout), parser-style single-statement guard, `SET` no longer concatenated. Re-tested live: `pg_read_file`, multi-statement, `EXPLAIN ANALYZE`, `set_config`, `$$` quoting all rejected; plain SELECT/WITH/EXPLAIN work; role-level denial confirmed directly with `psql`. | **VERIFIED** |
| 2026-11-11 | **B2** Python runner: scrubbed environment, `python -I`, throwaway empty cwd, NPROC/CORE limits, network + process-spawn blocked in-interpreter, user code run via `runpy` (fixes `from __future__`). Live test: `SECRET_KEY` → `None`. **Residual risk:** the in-interpreter guards are best-effort and the child can still read world-readable container files; true isolation needs a separate no-network runner container/gVisor (still pending). | **MITIGATED, not fully isolated** |
| 2026-11-11 | **B3** `/projects/{id}` and `/projects/{id}/questions` accept UUID or slug. Live: 200 for all 3 projects. | **VERIFIED** |
| 2026-11-11 | **B4** Resume parser no longer injects hardcoded facts/projects; whole-word skill matching; projects/facts derived only from uploaded text. Live: generic DOCX yields only its own skills/project/fact. 3 unit tests added. | **VERIFIED** |
| 2026-11-11 | **B5** `PATCH /resumes/{id}` (replace skills/projects, append facts) and `DELETE /resumes/{id}/facts/{fact_id}`; upload hardening (server-generated filename, 10 MB cap → 413, magic-byte check, case-insensitive ext). Live-tested incl. 404 for foreign/unknown id. | **VERIFIED** (no UI yet) |
| 2026-11-11 | **B6** `/questions?search=` wired with escaped ILIKE. | **VERIFIED** |
| 2026-11-11 | Tests: 3 → 12 passing (`test_sandboxes.py`, `test_resume_parser.py`). | **VERIFIED** (`pytest`: 12 passed) |
| 2026-11-11 | Audit test data (user `audit@example.com`, its resumes and uploaded files) removed from dev DB/volume. | done |

### Not done in this pass (still open)
- **Content (P2):** while this audit ran, another process started replacing `seed.py` with a curated pipeline (`backend/app/content/`, `discover.py`, uncommitted). I did not touch those files. The 857 filler questions and 45+35 filler problems are **still in the running database** and this audit has not verified the new pipeline.
- **B7 / P3 frontend:** Mermaid rendering, Monaco, Bootstrap 5, grouped sidebar, resume-edit UI: not started.
- **P4:** real Alembic migration, services/repositories split, exception handler, remaining docs, broader tests.
- Docker-level isolation for the Python runner (see B2).
- Frontend was not browser-tested in this pass.
