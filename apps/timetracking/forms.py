"""Forms for time-entry creation and editing."""

from django import forms

from apps.core.forms import date_input_widget
from apps.timetracking.models import TimeEntry


class TimeEntryForm(forms.ModelForm):
    """ModelForm used when creating a new ``TimeEntry``."""

    class Meta:
        model = TimeEntry
        fields = [
            "proposal",
            "date",
            "hours",
            "description",
            "billable",
            "override_status_restriction",
        ]
        widgets = {
            "date": date_input_widget(),
        }


class TimeEntryUpdateForm(forms.ModelForm):
    """ModelForm used when editing an existing ``TimeEntry``.

    Drops the ``proposal`` field so the entry can't be reassigned.
    """

    class Meta:
        model = TimeEntry
        fields = [
            "date",
            "hours",
            "description",
            "billable",
            "override_status_restriction",
        ]
        widgets = {
            "date": date_input_widget(),
        }
