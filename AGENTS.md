# Freelancer Tracker

Django 6.0.5 project (Python 3.14+, uv package manager).

## Commands

```bash
uv sync              # Install dependencies
django-admin startproject .   # Initialize Django project (run once)
python manage.py migrate    # Run migrations
python manage.py runserver   # Start dev server
python manage.py test       # Run tests
```

## Structure

- `main.py` - Currently unused stub
- Django not yet initialized (no `manage.py`, settings, or apps exist)
- Create migrations, models, and views after running `startproject`

## Notes

- Use `django-admin` or `python -m django` if `manage.py` missing
- This is a fresh project; most boilerplate needs creation