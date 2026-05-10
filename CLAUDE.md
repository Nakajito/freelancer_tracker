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

## Key constraints

- `sent_date` is optional (`null=True`) on `Proposal` — analytics must handle null via `created_at` fallback.
- `TimeEntry.clean()` blocks creation unless proposal is `ACCEPTED` (or `override_status_restriction=True`).
- `RecurringRetainer` is 1:1 with `Proposal`; the generator command is idempotent.
- Deployed on Coolify via Docker. `SEED_DEMO=1` env var triggers seed on container start. See `deploy/COOLIFY.md`.
