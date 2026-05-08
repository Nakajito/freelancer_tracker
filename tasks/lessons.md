# Lessons Learned

## Corrections made during Phase 1

1. **Circular import**: Had to move ProposalManager definition to avoid circular import between models.py and querysets.py. Fixed by using lazy imports inside the QuerySet methods.

2. **Settings structure**: Initially tried to put settings in config/settings/ but this caused import issues. Fixed by using config/settings_base.py, config/settings_dev.py directly.

3. **Missing middleware**: Forgot to add allauth.account.middleware.AccountMiddleware which is required by django-allauth 0.64+.

4. **Migrations directories**: Had to manually create migrations directories and __init__.py files for each app before running makemigrations.