from django import forms

from apps.core.forms import date_input_widget
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus


class ProposalFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("", "All Statuses")] + list(ProposalStatus.choices),
        required=False,
        label="Status",
    )
    platform = forms.ChoiceField(
        choices=[("", "All Platforms")] + list(Platform.choices),
        required=False,
        label="Platform",
    )


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = [
            "title",
            "platform",
            "client",
            "proposal_text",
            "amount",
            "status",
            "sent_date",
            "expected_response_date",
            "job_url",
            "proposal_url",
            "tags",
        ]
        widgets = {
            "sent_date": date_input_widget(),
            "expected_response_date": date_input_widget(),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "email", "notes"]
