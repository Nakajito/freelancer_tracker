"""Username resolution for django-axes.

axes reads the identifier from two different places and they do not agree in
this project:

* the pre-authentication lockout check calls it with no credentials, so it
  falls back to ``request.POST`` -- where allauth's field is named ``login``
  (and Django's admin form uses ``username``);
* the post-failure signal supplies a ``credentials`` dict whose key is
  allauth's ``LoginMethod`` enum member, not the literal string ``"login"``.

A single ``AXES_USERNAME_FORM_FIELD`` cannot satisfy both, so it silently
resolved to ``None`` on the signal path and the username dimension of
``AXES_LOCKOUT_PARAMETERS`` never carried a value.
"""

from typing import Any

# Ordered by specificity. LoginMethod is a str subclass, so a plain "email"
# lookup matches the enum key allauth uses.
_CREDENTIAL_KEYS = ("email", "login", "username")

_FORM_FIELDS = ("login", "username", "email")


def get_username(request: Any, credentials: dict | None = None) -> str | None:
    """Return a normalized login identifier, or ``None`` when absent."""
    if credentials:
        for key in _CREDENTIAL_KEYS:
            value = credentials.get(key)
            if value:
                return _normalize(value)

    data = getattr(request, "data", None)
    if data is None:
        data = getattr(request, "POST", None)
    if data is None:
        return None

    for field in _FORM_FIELDS:
        value = data.get(field)
        if value:
            return _normalize(value)

    return None


def _normalize(value: Any) -> str:
    """Fold case and whitespace so ``A@b.com`` and ``a@b.com`` share a bucket."""
    return str(value).strip().lower()
