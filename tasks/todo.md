# Todo - Freelancer Tracker

## Fase 1: Bootstrap - COMPLETED ✅
- [x] Setup Django project with settings split
- [x] Create all apps (core, accounts, proposals, followups, timetracking, templates_app, dashboard, exports)
- [x] Setup django-allauth
- [x] Create base templates
- [x] Run migrations
- [x] Create seed_demo script
- [x] Verify server works
- [x] Run seed_demo successfully

## Fase 2: Core + Proposals CRUD - COMPLETED ✅
- [x] Create models (Client, Tag, Proposal)
- [x] Create custom QuerySet
- [x] Create views (List, Detail, Create, Update, Delete)
- [x] Create templates
- [x] Add filter form
- [x] Write tests (10 passing)

## Fase 3: Status engine + ActivityLog - COMPLETED ✅
- [x] Create signals for status change
- [x] Create transition service
- [x] Create duplicate-check service  
- [x] Add DRF endpoint for duplicate-check
- [x] Add webhook stub endpoint

## Fase 4: Follow-ups - COMPLETED ✅
- [x] Create model and services
- [x] Add auto-suggest service
- [x] Add overdue/upcoming queries
- [x] Add HTMX inline complete
- [x] Add dashboard widget data

## Fase 5: Time tracking - COMPLETED ✅
- [x] Create model with clean() restriction
- [x] Create billable aggregation service
- [x] Create recurring retainer generator
- [x] Create generate_retainer_entries mgmt command

## Fase 6: Templates - COMPLETED ✅
- [x] Create placeholder renderer service
- [x] Add preview view
- [x] Add "use template" action

## Fase 7: Dashboard + Exports - COMPLETED ✅
- [x] Add Chart.js views
- [x] Add CSV/JSON DRF exports
- [x] Add monthly HTML summary
- [x] Create send_digest mgmt command
- [x] Add webhook stub

## Fase 8: Hardening - COMPLETED ✅
- [x] Setup CI workflow (.github/workflows/ci.yml)
- [x] Setup CodeQL workflow (.github/workflows/codeql.yml)
- [x] Create Docker setup (Dockerfile, docker-compose.yml, entrypoint.sh)
- [x] N+1 queries optimized with select_related/prefetch_related
- [x] Management commands (seed_demo, generate_retainer_entries, send_digest)
- [ ] Create Sphinx docs (pendiente)
- [ ] Push coverage to 85% (requiere más tests)

## Mejora UI, i18n y cuenta - COMPLETED ✅

### Iteración 1: Fixes UI y datos
- [x] Reemplazar mensajes duplicados por parcial reutilizable con auto-dismiss y botón de cierre.
- [x] Exponer todos los estados de `ProposalStatus` en el funnel del dashboard, incluyendo conteos cero.
- [x] Renderizar filtros de `proposals/` desde `ProposalStatus.choices` y `Platform.choices`.
- [x] Corregir `Amount (USD)` para que el símbolo `$` no se sobreponga al input.
- [x] Permitir crear cliente desde `proposals/create/`.
- [x] Filtrar `client` y `tags` por usuario en `ProposalForm`.

### Iteración 2: Tema e idioma
- [x] Agregar preferencias `system/light/dark` y aplicar tema desde `<html>`.
- [x] Agregar selector global de tema.
- [x] Configurar `LocaleMiddleware`, `LANGUAGES`, `LOCALE_PATHS` y rutas `i18n/`.
- [x] Agregar selector global de idioma.
- [x] Traducir UI visible principal a español/inglés.

### Iteración 3: Panel de usuario
- [x] Agregar `/accounts/profile/`, `/accounts/preferences/` y `/accounts/deactivate/`.
- [x] Extender usuario con `avatar`, `theme_preference` y `language_preference`.
- [x] Permitir editar nombre, email, avatar, tema e idioma.
- [x] Enlazar cambio de contraseña de allauth.
- [x] Desactivar cuenta con confirmación de contraseña, logout y datos preservados.

### Verificación
- [x] Actualizar `README.md`.
- [x] Actualizar `tasks/lessons.md` si se corrigen patrones.
- [x] Ejecutar `uv run pytest`.
- [x] Ejecutar `uv run ruff check . && uv run ruff format --check .`.
- [x] Ejecutar `uv run mypy apps config`.
- [x] Ejecutar `bin/build-css.sh`.
