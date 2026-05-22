from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.forms import date_input_widget
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, PricingType


class ProposalFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("", _("All Statuses"))] + list(ProposalStatus.choices),
        required=False,
        label=_("Status"),
    )
    platform = forms.ChoiceField(
        choices=[("", _("All Platforms"))] + list(Platform.choices),
        required=False,
        label=_("Platform"),
    )


class ProposalForm(forms.ModelForm):
    new_client_name = forms.CharField(
        required=False,
        label=_("New client name"),
        help_text=_("Use this when the client is not in your list yet."),
    )
    new_client_email = forms.EmailField(
        required=False,
        label=_("New client email"),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            self.fields["client"].queryset = Client.objects.filter(owner=user)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(
                owner=user
            )
        self.fields["amount"].widget.attrs["class"] = (
            self.fields["amount"].widget.attrs.get("class", "") + " currency-input"
        ).strip()
        self.fields["amount"].widget.attrs["style"] = "padding-left: 2.25rem;"
        self.fields["hourly_rate"].widget.attrs["class"] = (
            self.fields["hourly_rate"].widget.attrs.get("class", "") + " currency-input"
        ).strip()
        self.fields["hourly_rate"].widget.attrs["style"] = "padding-left: 2.25rem;"

    def clean(self):
        cleaned_data = super().clean()
        pricing_type = cleaned_data.get("pricing_type")
        if pricing_type == PricingType.HOURLY:
            if not cleaned_data.get("hourly_rate"):
                self.add_error("hourly_rate", _("Required for hourly pricing."))
            if not cleaned_data.get("estimated_hours"):
                self.add_error("estimated_hours", _("Required for hourly pricing."))
        return cleaned_data

    class Meta:
        model = Proposal
        fields = [
            "title",
            "platform",
            "client",
            "proposal_text",
            "amount",
            "pricing_type",
            "hourly_rate",
            "estimated_hours",
            "status",
            "sent_date",
            "expected_response_date",
            "job_url",
            "proposal_url",
            "tags",
            "new_client_name",
            "new_client_email",
        ]
        widgets = {
            "sent_date": date_input_widget(),
            "expected_response_date": date_input_widget(),
        }

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_client = self.cleaned_data.get("client")
        new_client_name = (self.cleaned_data.get("new_client_name") or "").strip()
        new_client_email = (self.cleaned_data.get("new_client_email") or "").strip()

        if selected_client:
            instance.client = selected_client
        elif new_client_name and self.user is not None:
            client, created = Client.objects.get_or_create(
                owner=self.user,
                name=new_client_name,
                defaults={"email": new_client_email},
            )
            if not created and new_client_email and not client.email:
                client.email = new_client_email
                client.save(update_fields=["email"])
            instance.client = client

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "email", "notes"]
