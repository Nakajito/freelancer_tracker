# Pipelancer — Agent Guide

Django 6 web app for freelancers to track proposals, clients, follow-ups, hours, with dashboards, templates, reminders. Stack locked: Django 6 + DRF (narrow), Python 3.14, `uv`, ruff, mypy, pytest-django + factory-boy, django-allauth (session), Bootstrap 5 + HTMX, Chart.js, Sphinx, Docker, GitHub Actions CI.

Full plan: [plans/freelance-proposal-tracker.md](plans/freelance-proposal-tracker.md).

## User decisions (locked)

- CSS: **Bootstrap 5**
- Auth: **Allauth session-only**
- Reports: **HTML only** (no PDF)
- Charts: **Chart.js**
- DB: SQLite dev / Postgres 16 prod (via `dj-database-url`)

## Process rules (must follow)

- **Plan Mode default**: any task >3 steps or with architectural decisions → write `tasks/todo.md` plan first. If a plan fails → stop and replan.
- **Subagents**: dispatch one per investigation/exploration to save context.
- **TDD**: tests before implementation. Per-phase order: model → QuerySet → service → form → view tests.
- **Continuous improvement**: after every correction append to `tasks/lessons.md` with pattern + rule. Review at session start.
- **Verification before "done"**: run tests, lint, typecheck, dev server walkthrough. Ask "would a staff engineer approve?".
- **Balanced elegance**: pause on non-trivial changes; pick elegant over hacky; skip only obvious fixes.
- **Autonomous bug fixing**: fix without asking, show logs/errors/tests. Fix failing CI without prompting.
- **Minimal impact**: touch only what's necessary. No temporary patches — root cause only.

## Architecture rules (per `.agents/skills/django-patterns/SKILL.md`)

- **App split by bounded context**, not by data type. Apps: `core`, `accounts`, `proposals`, `followups`, `timetracking`, `templates_app`, `dashboard`, `exports`.
- **Service layer** for multi-model logic, transactions, external I/O. Models hold only `__str__`, `clean()`, computed props.
- **Custom QuerySets** chainable: `Proposal.objects.for_user(u).pending_response().with_client()`. Mandatory `select_related/prefetch_related` on list views.
- **Signals** registered in `apps.py:ready()`: auto-set `actual_response_date` on status transition; ActivityLog on status change + follow-up completion.
- **Pydantic v2** for service-layer DTOs only (`DuplicateCheckResult`, `DashboardMetrics`). Not for ORM-shaped data.
- **OwnerQuerysetMixin** + `LoginRequiredMixin` on every CBV. Per-user isolation tested explicitly.
- **DRF surface narrow**: `POST /api/webhooks/proposal-events/` (HMAC stub), `GET /api/proposals/duplicate-check/`, CSV/JSON export. All other UX via Django Forms + HTMX.
- **Settings split**: `config/settings/{base,dev,prod,test}.py` via django-environ.

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

## Domain model summary

- `core.TimeStampedModel` (abstract): `created_at`, `updated_at`.
- `core.OwnedModel` (abstract): `owner = FK(User, CASCADE)`. Every domain model inherits.
- `core.ActivityLog`: GenericFK + `actor`, `verb`, `metadata=JSONField`. Index `(content_type, object_id, -created_at)`.
- `proposals.Client`: `(owner, name)` unique.
- `proposals.Tag`: `(owner, slug)` unique.
- `proposals.Proposal`: title, platform (TextChoices: Upwork/Fiverr/Freelancer/Workana/LinkedIn/Other), client FK, proposal_text, `amount=Decimal(12,2)`, status (TextChoices: Draft/Sent/Viewed/Responded/Negotiating/Accepted/Rejected/Archived), sent_date, expected_response_date, actual_response_date, job_url, proposal_url, tags M2M, `paid=Bool`. Indexes `(owner,status)`, `(owner,platform,sent_date)`, `(client,sent_date)`. CheckConstraint `amount>=0`. Computed `response_time` property.
- `followups.FollowUp`: proposal FK, description, due_date, completed, completed_at, notes. Index `(due_date, completed)`.
- `timetracking.TimeEntry`: proposal FK, date, `hours=Decimal(5,2)`, description, `billable=Bool`, `override_status_restriction=Bool`. `clean()` blocks unless proposal Accepted or override true.
- `timetracking.RecurringRetainer`: 1:1 proposal, monthly_hours, day_of_month, active. Idempotent generator service.
- `templates_app.ProposalTemplate`: name, body, owner, `placeholders=JSONField`. Renderer uses `string.Template` (safe) for `{client}`, `{project}`, `{amount}`, `{date}`.

## Phased delivery (drives `tasks/todo.md`)

1. **Bootstrap** — startproject, settings split, custom User, allauth, base template, CI skeleton, Docker, docs scaffold. Exit: green CI.
2. **Core + Proposals CRUD** — abstracts, Client, Tag, Proposal, QuerySet, forms, CBVs, filter form, owner-isolation tests.
3. **Status engine + ActivityLog** — signals, transition service, duplicate-detect service + DRF endpoint, HTMX inline duplicate warning.
4. **Follow-ups** — model, auto-suggest 3-day service, overdue/upcoming queries, HTMX inline complete, dashboard widget data.
5. **Time tracking** — model + clean() restriction, billable aggregation service, recurring retainer + `generate_retainer_entries` mgmt command.
6. **Templates** — model, placeholder renderer, preview view, "use template" action seeding Proposal create form.
7. **Dashboard + Exports** — funnel/conversion/forecast/hourly-rate services, Chart.js views, CSV/JSON DRF exports, monthly HTML summary, digest widget + `send_digest` mgmt command, webhook stub.
8. **Hardening** — Sphinx pages, CodeQL workflow, prod settings audit, N+1 sweep, coverage push, README + seed script + screenshots.

## Commands

```bash
uv sync                                          # Install deps
uv run python manage.py migrate                  # Migrations
uv run python manage.py seed_demo                # Demo data
uv run python manage.py runserver                # Dev server
uv run python manage.py send_digest              # Daily follow-up digest
uv run python manage.py generate_retainer_entries  # Recurring retainer time entries
uv run pytest --cov --cov-fail-under=85          # Tests + coverage gate
uv run ruff check . && uv run ruff format --check .
uv run mypy apps config
sphinx-build -W docs docs/_build                 # Docs build
docker compose -f deploy/docker-compose.yml up --build  # Local stack
```

## Verification checklist (before declaring done)

- `pytest --cov --cov-fail-under=85` green; service modules ≥95%.
- ruff + mypy clean.
- E2E walk on dev server: create proposal → Sent → Responded (assert auto `actual_response_date` + ActivityLog row) → follow-up → Accepted → time entry → dashboard charts → CSV export → monthly HTML summary → duplicate-check warning (same client+platform within 30 days).
- `docker compose up --build` brings web + db up; migrations + seed run; reachable on `:8000`.
- `sphinx-build -W` no warnings.
- CI green: lint + typecheck + test + docs + CodeQL.

## Skills available

- `.agents/skills/django-patterns/SKILL.md` — production Django architecture (apply for app split, services, QuerySets, signals, indexing, N+1 prevention).
- `.agents/skills/frontend-design/SKILL.md` — frontend UI guidance.

## Notes

- Django not yet initialized — Phase 1 runs `startproject` + settings split.
- `main.py` is legacy stub; safe to delete during Phase 1.
- `tasks/todo.md` and `tasks/lessons.md` created in Phase 1 init; lessons appended on every correction.
