# Lessons Learned

## Corrections made during Phase 1

1. **Circular import**: Had to move ProposalManager definition to avoid circular import between models.py and querysets.py. Fixed by using lazy imports inside the QuerySet methods.

2. **Settings structure**: Initially tried to put settings in config/settings/ but this caused import issues. Fixed by using config/settings_base.py, config/settings_dev.py directly.

3. **Missing middleware**: Forgot to add allauth.account.middleware.AccountMiddleware which is required by django-allauth 0.64+.

4. **LocaleMiddleware URL-prefix priority**: When using `i18n_patterns(prefix_default_language=True)`, `LocaleMiddleware` activates language from the URL prefix *before* the cookie. Redirecting to a raw Referer URL (e.g. `/en/dashboard/`) after saving a new language preference re-activates the old language, making the switch appear broken. Rule: always call `translate_url(url, new_lang)` (from `django.urls`) before redirecting after a language change. Note: in Django 6, `translate_url` lives in `django.urls`, NOT `django.utils.translation`.

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

## CSS specificity: global element selectors vs Tailwind utilities

**Pattern**: `forms.css` applied `padding: 0.75rem 1rem` to bare element selectors (`input[type=email]`, `input[type=password]`). These selectors have specificity 0,0,1,1 (element + attribute), which beats Tailwind utility classes with specificity 0,0,1,0, silently overriding padding values and causing icon-overlap in auth inputs with `pl-11`.

**Rule**: Global `forms.css` rules targeting bare element selectors are a specificity trap. Auth pages that hand-roll inputs with Tailwind must mark those inputs with a class (e.g. `.auth-field`) and exclude them via `:not(.auth-field)` in `forms.css`.

**Rule**: When removing a feature (dark mode), update all its touch points in one pass: CSS `@theme` tokens, template `data-theme` attribute, JS preference logic, context processors, forms, and tests. Leaving any one untouched causes test failures or lingering dead code.

**Rule**: When forms.py removes a field, audit all tests that POST that field and assert on it — they will fail silently or with confusing errors if not updated.
