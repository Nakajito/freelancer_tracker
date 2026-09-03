"""Additional tests to push coverage above 85%."""

import hashlib
import hmac
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.followups.models import FollowUp
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus
from apps.templates_app.models import ProposalTemplate
from apps.timetracking.models import RecurringRetainer, TimeEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def template(db, user):
    return ProposalTemplate.objects.create(
        owner=user,
        name="My Template",
        body="Hello {{client_name}}, regarding {{project_title}}.",
    )


@pytest.fixture
def accepted_proposal(db, user, client_model):
    return Proposal.objects.create(
        owner=user,
        title="Accepted Proposal",
        client=client_model,
        status=ProposalStatus.ACCEPTED,
        amount=Decimal("2000.00"),
        sent_date=date.today(),
    )


@pytest.fixture
def time_entry(db, accepted_proposal):
    return TimeEntry.objects.create(
        proposal=accepted_proposal,
        date=date.today(),
        hours=Decimal("4.00"),
        billable=True,
    )


@pytest.fixture
def followup(db, proposal):
    return FollowUp.objects.create(
        proposal=proposal,
        description="Check in",
        due_date=date.today() + timedelta(days=3),
    )


@pytest.fixture
def overdue_followup(db, proposal):
    return FollowUp.objects.create(
        proposal=proposal,
        description="Overdue",
        due_date=date.today() - timedelta(days=5),
    )


@pytest.fixture
def completed_followup(db, proposal):
    return FollowUp.objects.create(
        proposal=proposal,
        description="Done",
        due_date=date.today() - timedelta(days=1),
        completed=True,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHealthView:
    def test_healthz_returns_ok(self, client):
        response = client.get(reverse("healthz"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# SEO views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeoViews:
    def test_robots_txt(self, client):
        response = client.get(reverse("robots_txt"))
        assert response.status_code == 200
        assert b"User-agent" in response.content
        assert b"Disallow: /admin/" in response.content

    def test_security_txt(self, client):
        response = client.get(reverse("security_txt"))
        assert response.status_code == 200
        assert b"Contact:" in response.content
        assert b"Expires:" in response.content

    def test_change_password_redirect(self, client):
        response = client.get(reverse("change_password"))
        assert response.status_code == 302
        assert "/accounts/password/change/" in response["Location"]


# ---------------------------------------------------------------------------
# Proposals API views (IsAuthenticated)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProposalApiViews:
    def test_duplicate_check_no_duplicate(self, authed_client, client_model):
        url = reverse("duplicate-check")
        data = {"client_id": client_model.pk, "platform": "upwork"}
        response = authed_client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json()["is_duplicate"] is False

    def test_duplicate_check_client_not_found(self, authed_client):
        url = reverse("duplicate-check")
        data = {"client_id": 99999, "platform": "upwork"}
        response = authed_client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 404

    def test_duplicate_check_with_existing(self, authed_client, client_model, user):
        Proposal.objects.create(
            owner=user,
            title="Existing",
            client=client_model,
            platform=Platform.UPWORK,
            sent_date=date.today(),
        )
        url = reverse("duplicate-check")
        data = {"client_id": client_model.pk, "platform": "upwork"}
        response = authed_client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json()["is_duplicate"] is True

    def test_proposal_export_json(self, authed_client, proposal):
        url = reverse("proposal-export-json")
        response = authed_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_proposal_export_csv(self, authed_client, proposal):
        url = reverse("proposal-export-csv")
        response = authed_client.get(url)
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]


# ---------------------------------------------------------------------------
# Exports webhook (AllowAny)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebhookProposalEvents:
    def _make_sig(self, payload: bytes) -> str:
        return hmac.new(
            key=b"webhook-secret-key",
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def test_valid_event_no_signature(self, client):
        url = reverse("webhook-proposal-events")
        payload = json.dumps({"event_type": "proposal.created", "proposal_id": 1})
        response = client.post(url, data=payload, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["status"] == "received"

    def test_valid_event_with_correct_signature(self, client):
        url = reverse("webhook-proposal-events")
        payload = json.dumps({"event_type": "proposal.updated", "proposal_id": 2})
        sig = self._make_sig(payload.encode())
        response = client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
        )
        assert response.status_code == 200

    def test_invalid_signature_rejected(self, client):
        url = reverse("webhook-proposal-events")
        payload = json.dumps({"event_type": "proposal.deleted", "proposal_id": 3})
        response = client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_X_SIGNATURE="badsignature",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Proposals views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProposalListViewFilters:
    def test_filter_by_status(self, authed_client, user, client_model):
        Proposal.objects.create(
            owner=user, title="Draft", client=client_model, status=ProposalStatus.DRAFT
        )
        response = authed_client.get(reverse("proposal-list") + "?status=draft")
        assert response.status_code == 200

    def test_filter_by_platform(self, authed_client, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Upwork",
            client=client_model,
            platform=Platform.UPWORK,
        )
        response = authed_client.get(reverse("proposal-list") + "?platform=upwork")
        assert response.status_code == 200


@pytest.mark.django_db
class TestProposalCreateView:
    def test_create_proposal_redirects(self, authed_client, client_model):
        data = {
            "title": "New Proposal",
            "platform": "upwork",
            "client": client_model.pk,
            "amount": "500.00",
            "pricing_type": "fixed",
            "status": "draft",
            "proposal_text": "",
            "sent_date": "",
            "expected_response_date": "",
            "job_url": "",
            "proposal_url": "",
            "tags": [],
        }
        response = authed_client.post(reverse("proposal-create"), data=data)
        assert response.status_code == 302
        assert Proposal.objects.filter(title="New Proposal").exists()


@pytest.mark.django_db
class TestProposalUpdateView:
    def test_update_proposal_redirects(self, authed_client, proposal):
        data = {
            "title": "Updated Title",
            "platform": "other",
            "amount": "999.00",
            "pricing_type": "fixed",
            "status": "draft",
            "proposal_text": "",
            "sent_date": "",
            "expected_response_date": "",
            "job_url": "",
            "proposal_url": "",
            "tags": [],
        }
        url = reverse("proposal-update", kwargs={"pk": proposal.pk})
        response = authed_client.post(url, data=data)
        assert response.status_code == 302


@pytest.mark.django_db
class TestClientCreateView:
    def test_create_client_redirects(self, authed_client):
        data = {"name": "New Client", "email": "new@example.com", "notes": ""}
        response = authed_client.post(reverse("client-create"), data=data)
        assert response.status_code == 302
        assert Client.objects.filter(name="New Client").exists()


# ---------------------------------------------------------------------------
# Templates app views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateCreateView:
    def test_create_template_redirects(self, authed_client):
        data = {
            "name": "Cover Letter",
            "body": "Dear {{client_name}}, I am applying for {{project_title}}.",
        }
        response = authed_client.post(reverse("template-create"), data=data)
        assert response.status_code == 302
        assert ProposalTemplate.objects.filter(name="Cover Letter").exists()


@pytest.mark.django_db
class TestTemplateUpdateView:
    def test_update_template_redirects(self, authed_client, template):
        data = {
            "name": "Updated Template",
            "body": "Hello {{client_name}}, updated for {{project_title}}.",
        }
        url = reverse("template-update", kwargs={"pk": template.pk})
        response = authed_client.post(url, data=data)
        assert response.status_code == 302
        template.refresh_from_db()
        assert template.name == "Updated Template"


@pytest.mark.django_db
class TestTemplatePreviewView:
    def test_preview_renders_context(self, authed_client, template):
        url = reverse("template-preview", kwargs={"pk": template.pk})
        response = authed_client.get(url + "?client=Acme&project=Website&amount=$2,000")
        assert response.status_code == 200
        assert "rendered" in response.context

    def test_preview_default_context(self, authed_client, template):
        url = reverse("template-preview", kwargs={"pk": template.pk})
        response = authed_client.get(url)
        assert response.status_code == 200
        assert "rendered" in response.context


@pytest.mark.django_db
class TestTemplateUseView:
    def test_use_view_includes_clients(self, authed_client, template, client_model):
        url = reverse("template-use", kwargs={"pk": template.pk})
        response = authed_client.get(url)
        assert response.status_code == 200
        assert client_model in response.context["clients"]


# ---------------------------------------------------------------------------
# FollowUp views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFollowUpFilters:
    def test_filter_overdue(self, authed_client, overdue_followup):
        response = authed_client.get(reverse("followup-list") + "?filter=overdue")
        assert response.status_code == 200
        assert response.context["current_filter"] == "overdue"

    def test_filter_completed(self, authed_client, completed_followup):
        response = authed_client.get(reverse("followup-list") + "?filter=completed")
        assert response.status_code == 200
        assert response.context["current_filter"] == "completed"


@pytest.mark.django_db
class TestFollowUpCreateView:
    def test_create_form_filters_proposals(self, authed_client, proposal):
        response = authed_client.get(reverse("followup-create"))
        assert response.status_code == 200
        assert proposal in response.context["form"].fields["proposal"].queryset

    def test_create_followup_redirects(self, authed_client, proposal):
        data = {
            "proposal": proposal.pk,
            "description": "Check in",
            "due_date": str(date.today() + timedelta(days=7)),
        }
        response = authed_client.post(reverse("followup-create"), data=data)
        assert response.status_code == 302


@pytest.mark.django_db
class TestFollowUpCompleteView:
    def test_complete_followup(self, authed_client, followup):
        url = reverse("followup-complete", kwargs={"pk": followup.pk})
        response = authed_client.post(url)
        assert response.status_code == 302
        followup.refresh_from_db()
        assert followup.completed is True

    def test_complete_nonexistent_followup_returns_404(self, authed_client):
        """Unknown pk and another user's pk are indistinguishable: both 404."""
        url = reverse("followup-complete", kwargs={"pk": 99999})
        response = authed_client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TimeTracking views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryCreateView:
    def test_create_form_shows(self, authed_client, accepted_proposal):
        response = authed_client.get(reverse("timeentry-create"))
        assert response.status_code == 200
        qs = response.context["form"].fields["proposal"].queryset
        assert accepted_proposal in qs


@pytest.mark.django_db
class TestTimeEntryUpdateView:
    def test_update_redirects(self, authed_client, time_entry):
        data = {
            "date": str(date.today()),
            "hours": "6.00",
            "description": "More work",
            "billable": True,
        }
        url = reverse("timeentry-update", kwargs={"pk": time_entry.pk})
        response = authed_client.post(url, data=data)
        assert response.status_code == 302


@pytest.mark.django_db
class TestRecurringRetainerViews:
    def test_retainer_list(self, authed_client, accepted_proposal):
        RecurringRetainer.objects.create(
            proposal=accepted_proposal,
            monthly_hours=Decimal("40.00"),
            day_of_month=1,
            active=True,
        )
        response = authed_client.get(reverse("retainer-list"))
        assert response.status_code == 200

    def test_retainer_create_form_shows(self, authed_client, accepted_proposal):
        response = authed_client.get(reverse("retainer-create"))
        assert response.status_code == 200
        qs = response.context["form"].fields["proposal"].queryset
        assert accepted_proposal in qs


# ---------------------------------------------------------------------------
# FollowUp model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFollowUpModel:
    def test_str(self, proposal):
        fu = FollowUp.objects.create(
            proposal=proposal,
            description="Call",
            due_date=date.today(),
        )
        assert str(fu) == f"Follow-up for {proposal.title}"

    def test_mark_completed(self, proposal):
        fu = FollowUp.objects.create(
            proposal=proposal,
            description="Call",
            due_date=date.today() - timedelta(days=1),
        )
        assert fu.completed is False
        fu.mark_completed()
        assert fu.completed is True
        assert fu.completed_at is not None

    def test_is_overdue(self, proposal):
        fu = FollowUp.objects.create(
            proposal=proposal,
            description="Old",
            due_date=date.today() - timedelta(days=3),
        )
        assert fu.is_overdue is True


# ---------------------------------------------------------------------------
# TimeEntry and RecurringRetainer model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryModel:
    def test_str(self, accepted_proposal):
        entry = TimeEntry.objects.create(
            proposal=accepted_proposal,
            date=date.today(),
            hours=Decimal("3.00"),
        )
        assert str(entry) == f"3.00h on {accepted_proposal.title}"

    def test_clean_rejects_non_accepted(self, user, client_model):
        draft = Proposal.objects.create(
            owner=user,
            title="Draft",
            client=client_model,
            status=ProposalStatus.DRAFT,
        )
        entry = TimeEntry(
            proposal=draft,
            date=date.today(),
            hours=Decimal("2.00"),
        )
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            entry.clean()


@pytest.mark.django_db
class TestRecurringRetainerModel:
    def test_str(self, accepted_proposal):
        retainer = RecurringRetainer.objects.create(
            proposal=accepted_proposal,
            monthly_hours=Decimal("20.00"),
            day_of_month=15,
            active=True,
        )
        assert "20.00" in str(retainer)
        assert accepted_proposal.title in str(retainer)


# ---------------------------------------------------------------------------
# FollowUp services
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAutoSuggestService:
    def test_suggestion_with_sent_date(self, user, client_model):
        from apps.followups.services import AutoSuggestService

        p = Proposal.objects.create(
            owner=user,
            title="Sent Proposal",
            client=client_model,
            status=ProposalStatus.SENT,
            sent_date=date.today(),
        )
        suggestions = AutoSuggestService.suggest_follow_ups(p)
        assert len(suggestions) >= 1
        assert suggestions[0].proposal == p
        assert suggestions[0].reason != ""

    def test_suggestion_with_expected_date_future(self, user, client_model):
        from apps.followups.services import AutoSuggestService

        p = Proposal.objects.create(
            owner=user,
            title="Expected Proposal",
            client=client_model,
            status=ProposalStatus.SENT,
            expected_response_date=date.today() + timedelta(days=5),
        )
        suggestions = AutoSuggestService.suggest_follow_ups(p)
        dates = [s.suggested_date for s in suggestions]
        assert date.today() + timedelta(days=5) in dates

    def test_suggestion_with_expected_date_overdue(self, user, client_model):
        from apps.followups.services import AutoSuggestService

        p = Proposal.objects.create(
            owner=user,
            title="Overdue Expected",
            client=client_model,
            status=ProposalStatus.SENT,
            expected_response_date=date.today() - timedelta(days=2),
        )
        suggestions = AutoSuggestService.suggest_follow_ups(p)
        assert any("passed" in s.reason for s in suggestions)

    def test_follow_up_suggestion_init(self, proposal):
        from apps.followups.services import FollowUpSuggestion

        sugg = FollowUpSuggestion(
            proposal=proposal,
            suggested_date=date.today(),
            reason="Test reason",
        )
        assert sugg.proposal == proposal
        assert sugg.reason == "Test reason"
