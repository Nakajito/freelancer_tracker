from django import forms

from apps.followups.models import FollowUp


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ["proposal", "description", "due_date"]
        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }
