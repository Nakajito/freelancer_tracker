from pathlib import Path

from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.forms import date_input_widget
from apps.proposals.models import (
    Client,
    Platform,
    Proposal,
    ProposalStatus,
    PricingType,
)


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
    create_followup = forms.BooleanField(
        required=False,
        label=_("Schedule a follow-up on the expected response date"),
    )

    def _apply_currency_widget(self, field_name: str) -> None:
        attrs = self.fields[field_name].widget.attrs
        attrs["class"] = (attrs.get("class", "") + " currency-input").strip()
        attrs["style"] = "padding-left: 2.25rem;"

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            self.fields["client"].queryset = Client.objects.filter(owner=user)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(
                owner=user
            )
        self._apply_currency_widget("amount")
        self._apply_currency_widget("hourly_rate")

    def clean(self):
        cleaned_data = super().clean()
        pricing_type = cleaned_data.get("pricing_type")
        if pricing_type == PricingType.HOURLY:
            if cleaned_data.get("hourly_rate") is None:
                self.add_error("hourly_rate", _("Required for hourly pricing."))
            if cleaned_data.get("estimated_hours") is None:
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
            "create_followup",
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


class ProposalImportForm(forms.Form):
    """Upload a scraper-extracted file to bulk-create draft proposals."""

    MAX_SIZE = 5 * 1024 * 1024  # 5 MB, matches DATA_UPLOAD_MAX_MEMORY_SIZE (prod)
    ALLOWED_EXTENSIONS = {".json", ".csv", ".xlsx", ".md"}

    file = forms.FileField(
        label=_("Proposals file"),
        help_text=_("Accepted formats: .json, .csv, .xlsx, .md (max 5 MB)."),
        widget=forms.ClearableFileInput(
            attrs={"accept": ".json,.csv,.xlsx,.md"},
        ),
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                _("Unsupported file type. Use .json, .csv, .xlsx or .md.")
            )
        if uploaded.size > self.MAX_SIZE:
            raise forms.ValidationError(_("File too large (maximum 5 MB)."))
        return uploaded
