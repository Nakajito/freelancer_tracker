# Freelance Proposal Tracker — Final Plan

## Context

Repo `/home/nakajito/proyectos/freelancer_tracker` is empty scaffold (only `pyproject.toml` w/ Django 6.0.5, Python 3.14, `main.py` stub, `.agents/skills/django-patterns/SKILL.md`). Goal: full Django web app for freelancers to track proposals, clients, follow-ups, hours, with dashboards, templates, reminders, CI, Docker. Process rules mandate Plan Mode → TDD → subagents → `tasks/todo.md` + `tasks/lessons.md`, verification before completion.

User confirmed: **Bootstrap 5**, **Allauth session-only**, **HTML reports (no PDF)**, **Chart.js**.

## Stack (locked)

- Django 6.0 + Python 3.14, `uv`, ruff, mypy, Pydantic v2 (DTOs only), pytest-django + factory-boy
- DRF (narrow): webhook stub, duplicate-check, CSV/JSON export
- django-allauth (session), django-environ, dj-database-url, WhiteNoise
- SQLite dev / Postgres 16 prod, HTMX + Bootstrap 5, Chart.js
- Sphinx + sphinx-rtd-theme, Docker multi-stage, GitHub Actions CI (ruff, mypy, pytest+cov, CodeQL, docs build)

## Project layout

```
freelancer_tracker/
├── manage.py, pyproject.toml, uv.lock, .env.example
├── config/settings/{base,dev,prod,test}.py
├── config/{urls.py, wsgi.py, asgi.py}
├── apps/core/        (TimeStampedModel, OwnedModel, ActivityLog, mixins)
├── apps/accounts/    (custom User, allauth adapters)
├── apps/proposals/   (Proposal, Client, Tag, services, filters, signals)
├── apps/followups/   (FollowUp, auto-suggest service)
├── apps/timetracking/(TimeEntry, RecurringRetainer)
├── apps/templates_app/ (ProposalTemplate, placeholder renderer)
├── apps/dashboard/   (read-only metric services + views)
├── apps/exports/     (CSV/JSON, monthly HTML summary, webhook stub)
├── templates/{base,_sidebar,_navbar}.html + per-app dirs + partials/
├── static/{css,js,vendor}/
├── tests/{conftest.py, factories.py, integration/}
├── docs/{conf.py, index.rst, architecture.rst, models.rst, api.rst}
├── deploy/{Dockerfile, docker-compose.yml, entrypoint.sh, gunicorn.conf.py}
├── tasks/{todo.md, lessons.md}
├── plans/freelance-proposal-tracker.md
└── .github/workflows/{ci.yml, codeql.yml}
```

## Models (key fields, indexes, constraints)

- `core.TimeStampedModel` (abstract): `created_at`, `updated_at`.
- `core.OwnedModel` (abstract): `owner = FK(User, CASCADE)` — every domain model inherits, every QuerySet has `.for_user(u)`.
- `core.ActivityLog`: GenericFK + `actor`, `verb`, `metadata=JSONField`. Index `(content_type, object_id, -created_at)`.
- `proposals.Client`: `(owner, name)` unique.
- `proposals.Tag`: `(owner, slug)` unique.
- `proposals.Proposal`: title, platform (TextChoices), client FK, proposal_text, `amount=Decimal(12,2)`, status (TextChoices, default Draft), sent_date, expected_response_date, actual_response_date, job_url, proposal_url, tags M2M, `paid=Bool`. Indexes `(owner,status)`, `(owner,platform,sent_date)`, `(client,sent_date)`. CheckConstraint `amount>=0`. Computed `response_time` property.
- `followups.FollowUp`: proposal FK, description, due_date, completed, completed_at, notes. Index `(due_date, completed)`.
- `timetracking.TimeEntry`: proposal FK, date, `hours=Decimal(5,2)`, description, `billable=Bool`, `override_status_restriction=Bool`. `clean()` blocks unless proposal accepted or override true.
- `timetracking.RecurringRetainer`: 1:1 proposal, monthly_hours, day_of_month, active. Idempotent generator service.
- `templates_app.ProposalTemplate`: name, body, owner, `placeholders=JSONField`. Renderer uses `string.Template` (safe).

## Architecture rules (per `.agents/skills/django-patterns/SKILL.md`)

- **Service layer** for multi-model logic, transactions, external I/O. Models hold only `__str__`, `clean()`, computed props.
- **Custom QuerySets** chainable: `Proposal.objects.for_user(u).pending_response().with_client()`. Mandatory `select_related/prefetch_related` on list views.
- **Signals** (registered in `apps.py:ready()`): auto-set `actual_response_date` on status transition into Responded/Negotiating/Accepted/Rejected; write ActivityLog on status change + follow-up completion.
- **Pydantic v2 DTOs** for service inputs/outputs only (e.g., `DuplicateCheckResult`, `DashboardMetrics`). Not for ORM-shaped data.
- **OwnerQuerysetMixin** + `LoginRequiredMixin` on every CBV. Per-user isolation tested explicitly.

## Forms vs DRF

- Django Forms + HTMX for all CRUD, filters, follow-ups, time entries, templates.
- DRF only for: `POST /api/webhooks/proposal-events/` (HMAC-stub), `GET /api/proposals/duplicate-check/`, CSV/JSON export endpoints.

## Settings split

`base.py` reads env via django-environ. `dev.py` adds debug-toolbar + console email + SQLite. `prod.py` adds `SECURE_*`, WhiteNoise, structured logging, Postgres via `DATABASE_URL`. `test.py` in-memory SQLite, locmem email, dummy cache, disabled migrations for speed.

## Test strategy (TDD)

- pytest-django + factory-boy. Per-app `tests/` + factories. `conftest.py` fixtures: `user`, `other_user`, `authed_client`, `proposal`, `accepted_proposal`.
- Per-phase order: model tests → QuerySet tests → service tests (red→green) → form tests → view tests (auth + ownership isolation + template + HTMX fragments).
- Coverage: ≥85% overall, ≥95% on `services.py`. Enforced via `pytest --cov --cov-fail-under=85`.

## CI (`.github/workflows/ci.yml`)

Jobs: **lint** (`ruff check` + `ruff format --check`), **typecheck** (`mypy apps config`), **test** (`uv sync` → `pytest --cov`), **docs** (`sphinx-build -W`), **codeql** in `codeql.yml`. Postgres service container in test job for prod-parity. Cache via `setup-uv@v3`.

## Docker

- `deploy/Dockerfile` multi-stage: builder (uv compile wheels) → runtime (python:3.14-slim, non-root, gunicorn).
- `deploy/docker-compose.yml`: web + db(postgres:16) + nginx(optional) + volumes (static, media).
- `entrypoint.sh`: `migrate` → `collectstatic` → optional `seed_demo` (`SEED_DEMO=1`) → exec gunicorn.

## Phased delivery (8 phases — drives `tasks/todo.md`)

1. **Bootstrap** — startproject, settings split, custom User, allauth wiring, base template, CI skeleton, Docker, docs scaffold. Exit: green CI.
2. **Core + Proposals CRUD** — abstracts, Client, Tag, Proposal, QuerySet, forms, CBVs, filter form, owner-isolation tests.
3. **Status engine + ActivityLog** — signals, transition service, duplicate-detect service + DRF endpoint, HTMX inline duplicate warning on form blur.
4. **Follow-ups** — model, auto-suggest 3-day service, overdue/upcoming queries, HTMX inline complete, dashboard widget data.
5. **Time tracking** — model + clean() restriction, billable aggregation service, recurring retainer generator + `generate_retainer_entries` mgmt command.
6. **Templates** — model, placeholder renderer, preview view, "use template" action seeding Proposal create form.
7. **Dashboard + Exports** — funnel/conversion/forecast/hourly-rate services, Chart.js views, CSV/JSON DRF exports, monthly HTML summary, digest widget + `send_digest` mgmt command, webhook stub.
8. **Hardening** — Sphinx pages, CodeQL workflow, prod settings audit, N+1 sweep, coverage push, README + seed script + screenshots.

## Critical files (final)

- [config/settings/base.py](../config/settings/base.py)
- [apps/core/models.py](../apps/core/models.py) — abstract bases + ActivityLog
- [apps/proposals/models.py](../apps/proposals/models.py)
- [apps/proposals/querysets.py](../apps/proposals/querysets.py)
- [apps/proposals/services.py](../apps/proposals/services.py) — duplicate detection, status transition
- [apps/proposals/signals.py](../apps/proposals/signals.py)
- [apps/followups/services.py](../apps/followups/services.py)
- [apps/timetracking/services.py](../apps/timetracking/services.py) — billable totals + retainer generator
- [apps/templates_app/services.py](../apps/templates_app/services.py) — placeholder renderer
- [apps/dashboard/services.py](../apps/dashboard/services.py)
- [apps/exports/services.py](../apps/exports/services.py)
- [templates/base.html](../templates/base.html)
- [tests/conftest.py](../tests/conftest.py)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- [deploy/Dockerfile](../deploy/Dockerfile)
- [tasks/todo.md](../tasks/todo.md), [tasks/lessons.md](../tasks/lessons.md)

## Verification (end-to-end)

- `uv sync && uv run pytest --cov --cov-fail-under=85` — all green.
- `uv run ruff check . && uv run ruff format --check .` — clean.
- `uv run mypy apps config` — clean.
- `uv run python manage.py migrate && uv run python manage.py seed_demo && uv run python manage.py runserver` → log in as demo user, walk: create proposal → mark Sent → mark Responded (assert `actual_response_date` auto-set + ActivityLog row) → add follow-up → mark Accepted → log time entry → render dashboard charts → export CSV → render monthly HTML summary → trigger duplicate-check (same client+platform within 30 days) → confirm warning.
- `docker compose -f deploy/docker-compose.yml up --build` — web + db come up, migrations run, seed loads, app reachable on `:8000`.
- `sphinx-build -W docs docs/_build` — docs build with no warnings.
- CI run on push must pass lint + typecheck + test + docs + CodeQL.

## Process scaffolding

- `tasks/todo.md` initialized with 8 phase sections of checkbox items.
- `tasks/lessons.md` initialized empty; appended on every correction/rework.
- Each phase commits separately; failed CI fixed autonomously per spec.
