# Lessons Learned

## Corrections made during Phase 1

1. **Circular import**: Had to move ProposalManager definition to avoid circular import between models.py and querysets.py. Fixed by using lazy imports inside the QuerySet methods.

2. **Settings structure**: Initially tried to put settings in config/settings/ but this caused import issues. Fixed by using config/settings_base.py, config/settings_dev.py directly.

3. **Missing middleware**: Forgot to add allauth.account.middleware.AccountMiddleware which is required by django-allauth 0.64+.

4. **Migrations directories**: Had to manually create migrations directories and __init__.py files for each app before running makemigrations.

## Analytics filter coupling (period + year params)

**Pattern**: Filter form with two interdependent params (`period` and `year`) where `year` is only meaningful when `period="year"`.

**Rule — UX layer**: Hide the secondary param's input via JS when it doesn't apply. Use a Django template conditional (`{% if period != "year" %}style="display:none"{% endif %}`) so initial render is correct even without JS. Add a `change` event listener that calls a `sync()` function — no framework needed.

**Rule — service layer**: Services must accept explicit `start_date`/`end_date` (or `anchor_date`). Never let a service silently re-anchor to `date.today()` when the view has already computed the correct date range. The view is the single source of truth for date bounds.

**Rule — null sent_date**: `Proposal.sent_date` is optional. All analytics queries must use a Q filter fallback: `Q(sent_date__gte=start, sent_date__lt=end) | Q(sent_date__isnull=True, created_at__date__gte=start, created_at__date__lt=end)`.

**TDD**: Write tests for each period combination before implementing. The three required cases are `period=year&year=X`, `period=30&year=X` (year ignored), `period=90&year=X` (year ignored).

## UI preferences, static manifest, and service signatures

**Pattern**: Adding shared JS assets to templates while tests use manifest static storage can fail before `collectstatic` knows about the new files.

**Rule — test settings**: Use `django.contrib.staticfiles.storage.StaticFilesStorage` for `STORAGES["staticfiles"]` in tests so template rendering does not depend on a production manifest.

**Rule — CSS build**: `bin/build-css.sh` must invoke the Tailwind binary through `uv run` so the project-local dependency is available in clean shells and CI.

**Rule — service calls**: When a service signature changes to explicit date ranges, update every caller. `MonthlySummaryGenerator.generate()` requires `start_date`, `end_date`, and `period_label`; management commands must compute those values instead of passing year/month fragments.
