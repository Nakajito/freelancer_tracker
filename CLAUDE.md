# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                              # Install deps
uv run python manage.py migrate                      # Apply migrations
uv run python manage.py runserver                    # Dev server
uv run python manage.py seed_demo                    # Demo data (idempotent; --reset to wipe first)
uv run python manage.py seed_demo --reset            # Wipe + re-seed

uv run pytest                                        # All tests
uv run pytest tests/test_dashboard.py -k "period"   # Single test / filter
uv run pytest --no-cov                               # Skip coverage (faster)
uv run pytest --cov --cov-fail-under=75              # Coverage gate (75%)

uv run ruff check . && uv run ruff format --check .  # Lint
uv run mypy apps config                              # Type check

uv run python manage.py send_digest                  # Trigger follow-up digest email
uv run python manage.py generate_retainer_entries    # Generate monthly retainer time entries
docker compose -f deploy/docker-compose.yml up --build  # Local Docker stack

python bin/check-icons.py                            # Verify all template icons exist in font subset
python bin/check-icons.py --patch                    # Auto-patch missing icons (needs /tmp/material-symbols-full.ttf)
```

## Architecture

### App layout (bounded-context split)

| App | Responsibility |
|-----|----------------|
| `core` | `TimeStampedModel`, `OwnedModel` (abstract bases), `ActivityLog`, `OwnerQuerysetMixin` / `ProposalOwnerQuerysetMixin` |
| `accounts` | Custom `User`, allauth adapters |
| `proposals` | `Proposal`, `Client`, `Tag`; `ProposalQuerySet` with chainable filters |
| `followups` | `FollowUp`, auto-suggest service |
| `timetracking` | `TimeEntry`, `RecurringRetainer`, `generate_retainer_entries` management command |
| `templates_app` | `ProposalTemplate`, placeholder renderer (`string.Template`) |
| `dashboard` | Read-only metric services (`DashboardService`) + `MonthlySummaryView` |
| `exports` | `CSVExporter`, `JSONExporter`, `MonthlySummaryGenerator`; webhook stub |

### Ownership model

Every domain model inherits `OwnedModel` → `owner = FK(User, CASCADE)`. Per-user isolation is enforced at:
- **QuerySet level**: `Proposal.objects.for_user(user)` (all analytics services use this)
- **CBV level**: `OwnerQuerysetMixin` for models with a direct `owner` FK; `ProposalOwnerQuerysetMixin` for models reached via `proposal.owner` (FollowUp, TimeEntry)

### Service layer pattern

Multi-model logic lives in `services.py` per app, never in views or models.

- **`DashboardService`** (`apps/dashboard/services.py`) — all read-only metrics. Methods accept explicit date ranges (`start_date`, `end_date`). `get_earnings_chart` accepts optional `anchor_date` to anchor the 6-month window (defaults to today).
- **`MonthlySummaryGenerator.generate(user, start_date, end_date, period_label)`** (`apps/exports/services.py`) — aggregates proposals + time entries for arbitrary date ranges. Proposals without `sent_date` (null) are matched via `created_at__date` fallback.
- Models hold only `__str__`, `clean()`, and computed properties (e.g. `response_time`).

### Analytics date-range pattern

`MonthlySummaryView` derives `start_date` / `end_date` from `?period=30|90|year` + optional `?year=YYYY`. The `year` param is only meaningful when `period=year`; the template hides the year input via JS for other periods. All downstream services receive explicit dates — never re-derive from `date.today()` inside a service.

Proposals with `sent_date=None` use `created_at__date` as fallback (Q filter) in all analytics queries.

### Signals

`apps/proposals/signals.py` — `pre_save` caches `_old_status`; `post_save` writes `ActivityLog` rows on status change and on creation. Signals are registered in `apps.py:ready()`.

### DRF surface (narrow)

Only three endpoints use DRF:
- `POST /api/webhooks/proposal-events/` — HMAC stub
- `GET /api/proposals/duplicate-check/`
- `GET /api/proposals/export/json/` and `/csv/`

All other UX is Django Forms + HTMX.

### Settings

`config/settings/{base,dev,prod,test}.py` via `django-environ`. Tests use `DJANGO_SETTINGS_MODULE=config.settings.test`. Coverage threshold is **75%** (set in `pyproject.toml`).

### Test fixtures (`tests/conftest.py`)

Key fixtures: `user`, `other_user`, `authed_client`, `client_model`, `proposal` (DRAFT), `accepted_proposal`.

### Material Symbols icons (CRITICAL)

Icons use a **local woff2 subset** (`static/fonts/material-symbols/material-symbols-outlined-subset.vN.woff2`), NOT Google Fonts CDN. Only icons explicitly included in the subset render correctly.

**When adding a new icon:**
1. Run `python bin/check-icons.py` — it reports any icon missing from the font subset.
2. If missing: download the full font from Google Fonts (TTF URL from `fonts.googleapis.com/css2?family=Material+Symbols+Outlined`) to `/tmp/material-symbols-full.ttf`, then run `python bin/check-icons.py --patch`.
3. Update `static/css/icons.css` to reference the new `vN+1` font file.

**Never add an icon without verifying it renders** — missing icons show as text, not glyphs.

## Key constraints

- `sent_date` is optional (`null=True`) on `Proposal` — analytics must handle null via `created_at` fallback.
- `TimeEntry.clean()` blocks creation unless proposal is `ACCEPTED` (or `override_status_restriction=True`).
- `RecurringRetainer` is 1:1 with `Proposal`; the generator command is idempotent.
- Deployed on Coolify via Docker. `SEED_DEMO=1` env var triggers seed on container start. See `deploy/COOLIFY.md`.


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