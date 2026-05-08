from django import forms

from apps.timetracking.models import TimeEntry


class TimeEntryForm(forms.ModelForm):
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
            "date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }


class TimeEntryUpdateForm(forms.ModelForm):
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
            "date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }
