"""Forms for follow-up creation and editing."""

from django import forms

from apps.core.forms import date_input_widget
from apps.followups.models import FollowUp


class FollowUpForm(forms.ModelForm):
    """ModelForm for creating and editing ``FollowUp`` records."""

    class Meta:
        model = FollowUp
        fields = ["proposal", "description", "due_date"]
        widgets = {
            "due_date": date_input_widget(),
        }
