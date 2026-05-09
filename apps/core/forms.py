"""Reusable form helpers."""

from django import forms


def date_input_widget() -> forms.DateInput:
    """Return a ``DateInput`` configured for HTML5 date pickers.

    Sets ``type="date"`` so browsers render a native calendar, and
    ``format="%Y-%m-%d"`` so existing values populate correctly when
    editing. Use as the widget for any ``DateField`` exposed in a
    ``ModelForm``.

    Returns:
        Configured ``forms.DateInput`` instance.
    """
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
