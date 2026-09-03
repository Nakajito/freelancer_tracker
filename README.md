# Pipelancer - Freelance Proposal Tracker

A Django web application for freelancers to track proposals, clients, follow-ups, and hours with dashboards, templates, reminders, and analytics.

## Features

- **Proposal Management**: Create, track, and manage freelance proposals across platforms (Upwork, Fiverr, LinkedIn, Direct Clients)
- **Inline Client Creation**: Create a new client directly while drafting a proposal
- **Client Management**: Track client information and associated proposals
- **Follow-ups**: Schedule and track follow-up tasks for proposals
- **Time Tracking**: Log hours spent on projects with billable/non-billable tracking
- **Templates**: Reusable proposal templates with variable placeholders
- **Dashboard**: Real-time metrics on proposal funnel, conversion rates, and forecasts, including every proposal status
- **Analytics**: Monthly summaries, platform statistics, earnings forecasts
- **Preferences**: Light/dark/system theme and English/Spanish language switching — available to all users, including guests
- **User Profile**: Edit name, email, avatar, preferences, change password, and deactivate the account while preserving history

## Tech Stack

- **Backend**: Django 6, Python 3.14
- **API**: Django REST Framework (narrow surface)
- **Authentication**: django-allauth (session-based)
- **Frontend**: Tailwind CSS, Bootstrap 5, HTMX
- **Charts**: Chart.js
- **Database**: SQLite (dev) / PostgreSQL 16 (prod)
- **Testing**: pytest-django, factory-boy
- **Linting**: ruff, mypy
- **Deployment**: Docker, GitHub Actions CI

## Quick Start

```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create superuser (optional)
uv run python manage.py createsuperuser

# Seed demo data (optional)
uv run python manage.py seed_demo

# Start development server
uv run python manage.py runserver

# Rebuild CSS after template/style changes
bin/build-css.sh
```

Then open http://localhost:8000 in your browser.

## Project Structure

```
freelancer_tracker/
├── apps/
│   ├── core/          # Abstract models (OwnedModel, TimeStampedModel)
│   ├── accounts/      # Custom User + allauth adapters
│   ├── proposals/     # Proposal, Client, Tag models
│   ├── followups/     # Follow-up model + auto-suggest service
│   ├── timetracking/ # TimeEntry, RecurringRetainer
│   ├── templates_app/ # ProposalTemplate + placeholder renderer
│   ├── dashboard/     # Read-only metric services + views
│   └── exports/       # CSV/JSON exports, monthly summary
├── config/
│   ├── settings/      # Environment-specific settings
│   ├── urls.py        # URL configuration
│   └── wsgi.py       # WSGI entry point
├── templates/         # Django HTML templates
├── static/           # CSS, JavaScript
├── tests/             # Test configuration
└── docs/              # Sphinx documentation
```

## Commands

```bash
# Development
uv run python manage.py runserver        # Start dev server
uv run python manage.py seed_demo         # Generate demo data

# Testing
uv run pytest                            # Run all tests
uv run pytest --cov                      # Run with coverage

# Linting
uv run ruff check .                       # Check code
uv run ruff format .                      # Format code
uv run mypy apps config                 # Type check

# Database
uv run python manage.py makemigrations  # Create migrations
uv run python manage.py migrate           # Apply migrations
uv run python manage.py showmigrations  # Show migration status

# Management commands
uv run python manage.py send_digest              # Daily follow-up digest
uv run python manage.py generate_retainer_entries  # Recurring retainer entries

# Assets and i18n
bin/build-css.sh                                # Rebuild Tailwind CSS bundle
uv run python manage.py compilemessages         # Compile translation catalogs
```

## Design System

The project uses **Tailwind CSS** with custom design tokens following an editorial, monochrome aesthetic:

- **Palette**: Snow base `#F2F2F2`, Sand secondary `#EAE4D5`, Taupe accent/borders `#B6B09F`, Black `#000000` for text and CTAs
- **Fonts**: Libre Baskerville (serif, for headings H1–H3), Roboto (sans-serif, for body and UI labels)
- **Self-hosted**: All fonts (`.woff2`) served locally, no external CDN dependency
- **Border Radius**: 4px base, 8px large, 12px extra-large
- **CTAs**: Black background (`#000000`) with snow text; hover changes to taupe (`#B6B09F`)
- **Forms**: CSS variables via `forms.css`; auth inputs use `.auth-field` marker to opt out of global padding rules

## User Preferences & Account

Language (English/Español) control is available to **all users**. Theme is light-only (editorial palette).

| User type | Language persistence |
|---|---|
| Guest | Django language cookie via `/i18n/set_language/` |
| Authenticated | `User.language_preference` (DB) + language cookie |

Language switcher appears as an icon-button pill in the navbar on all pages (EN ↔ ES).

Authenticated users can also manage their account at:

- `/accounts/profile/` - profile, avatar, language, and password link
- `/accounts/preferences/` - POST endpoint used by the topbar language button
- `/accounts/deactivate/` - password-confirmed account deactivation (`is_active=False`)

Language switching uses Django i18n with English and Spanish catalogs.

## API Endpoints

For the narrow DRF surface:

- `GET /api/proposals/duplicate-check/` - Check for duplicate proposals
- `GET /api/proposals/export/json/` - Export proposals as JSON
- `GET /api/proposals/export/csv/` - Export proposals as CSV

## Deployment

```bash
# Local Docker stack
docker compose -f deploy/docker-compose.yml up --build

# Production (requires environment variables)
gunicorn_config/runtime.txt
```

## Contributing

1. Run tests: `uv run pytest --cov --cov-fail-under=85`
2. Run linting: `uv run ruff check . && uv run ruff format --check .`
3. Type check: `uv run mypy apps config`
4. Build docs: `sphinx-build -W docs docs/_build`

## License

MIT
