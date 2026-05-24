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

<!-- CODEGRAPH_START -->
## CodeGraph

This project has a CodeGraph MCP server (`codegraph_*` tools) configured. CodeGraph is a tree-sitter-parsed knowledge graph of every symbol, edge, and file. Reads are sub-millisecond and return structural information grep cannot.

### When to prefer codegraph over native search

Use codegraph for **structural** questions — what calls what, what would break, where is X defined, what is X's signature. Use native grep/read only for **literal text** queries (string contents, comments, log messages) or after you already have a specific file open.

| Question | Tool |
|---|---|
| "Where is X defined?" / "Find symbol named X" | `codegraph_search` |
| "What calls function Y?" | `codegraph_callers` |
| "What does Y call?" | `codegraph_callees` |
| "How does X reach/become Y? / trace the flow from X to Y" | `codegraph_trace` (one call = the whole path, incl. callback/React/JSX dynamic hops) |
| "What would break if I changed Z?" | `codegraph_impact` |
| "Show me Y's signature / source / docstring" | `codegraph_node` |
| "Give me focused context for a task/area" | `codegraph_context` |
| "See several related symbols' source at once" | `codegraph_explore` |
| "What files exist under path/" | `codegraph_files` |
| "Is the index healthy?" | `codegraph_status` |

### Rules of thumb

- **Answer directly — don't delegate exploration.** For "how does X work" / architecture questions, answer with 2-3 codegraph calls: `codegraph_context` first, then ONE `codegraph_explore` for the source of the symbols it surfaces. For a specific **flow** ("how does X reach Y") start with `codegraph_trace` from→to — one call returns the whole path with dynamic hops bridged — then ONE `codegraph_explore` for the bodies; don't rebuild the path with `codegraph_search` + `codegraph_callers`. Codegraph IS the pre-built index, so spawning a separate file-reading sub-task/agent — or running a grep + read loop — repeats work codegraph already did and costs more for the same answer.
- **Trust codegraph results.** They come from a full AST parse. Do NOT re-verify them with grep — that's slower, less accurate, and wastes context.
- **Don't grep first** when looking up a symbol by name. `codegraph_search` is faster and returns kind + location + signature in one call.
- **Don't chain `codegraph_search` + `codegraph_node`** when you just want context — `codegraph_context` is one call.
- **Don't loop `codegraph_node` over many symbols** — one `codegraph_explore` call returns several symbols' source grouped in a single capped call, while each separate node/Read call re-reads the whole context and costs far more.
- **Index lag**: the file watcher debounces ~500ms behind writes; don't re-query immediately after editing a file in the same turn.

### If `.codegraph/` doesn't exist

The MCP server returns "not initialized." Ask the user: *"I notice this project doesn't have CodeGraph initialized. Want me to run `codegraph init -i` to build the index?"*
<!-- CODEGRAPH_END -->

## Notes

- Django not yet initialized — Phase 1 runs `startproject` + settings split.
- `main.py` is legacy stub; safe to delete during Phase 1.
- `tasks/todo.md` and `tasks/lessons.md` created in Phase 1 init; lessons appended on every correction.

## Plan Mode (default)
- Plan si tarea >3 pasos o decisión arquitectónica. Si falla → para y replanifica.
- Usa plan también para verificación. Especifica requisitos upfront.

## Subagentes (ahorra contexto)
- Investiga, explora o analiza en paralelo con subagentes. Uno por tarea.

## Mejora continua
- Tras cada corrección: actualiza `tasks/lessons.md` con el patrón y reglas para no repetirlo.
- Revisa lecciones al iniciar cada sesión.

## Verificación antes de finalizar
- No marques completado sin pruebas. Compara comportamiento con el original.
- Pregunta: “¿Staff engineer aprobaría esto?”. Corre tests, revisa logs.

## Elegancia balanceada
- Cambios no triviales: pausa y busca solución más elegante.
- Si el fix es chapucero: implementa la versión elegante con lo que sabes ahora.
- Omitir solo en fixes obvios.

## Bug fixing autónomo
- Recibes un bug → arréglalo sin pedir ayuda. Señala logs, errores, tests.
- Arregla CI fallida sin instrucciones.

## Task Management
1. Plan → `tasks/todo.md` (ítems chequeables).
2. Verifica plan antes de implementar.
3. Marca progreso.
4. Explica cambios al final.
5. Documenta resultados en `todo.md`.
6. Lecciones → `lessons.md`.

## Principios
- Simplicidad: cambios mínimos.
- Sin parches temporales: encuentra causa raíz.
- Impacto mínimo: solo toca lo necesario.
- Realiza preguntas si tienes dudas para realizar las tareas y realiza propuestas.

## TDD
- Usa TDD siempre.

## Stack (por defecto)
- Python (última versión - MCP Context 7)
- Bootstrap 5 o Tailwind CSS (Preguntar primero),  SQLite (dev) / PostgreSQL (prod).

## UI/UX
- Responsivo, interfaces simples primero.

## CI/CD
- Genera configuración para GitHub Actions por defecto (a menos que se pida otro).

## Calidad y Estilo de Código
- Formateadores: Ruff 
- Seguridad: CodeQL 

## Pruebas (Testing):
- Pytest
- Cada vez que se agregue, modifique o elimine funcionalidad → actualizar los tests.

## Gestión de Paquetes y Entornos
- uv

## Tipado Estático (Type Checking)
- mypy, Pydantic

## Creación de Documentación
- Sphinx
- Skill "software-docs"
