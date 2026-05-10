import json
from decimal import Decimal
from datetime import date

import pytest
from django.urls import reverse

from apps.proposals.models import Client, Proposal, ProposalStatus, Platform
from apps.exports.api_views import webhook_proposal_events


@pytest.mark.django_db
class TestProposalAPIViews:
    def test_duplicate_check_endpoint_no_duplicate(
        self, user, client_model, authed_client
    ):
        from apps.proposals.services import DuplicateCheckService

        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is False

    def test_duplicate_check_endpoint_found(self, user, client_model):
        Proposal.objects.create(
            owner=user,
            title="Existing",
            client=client_model,
            platform=Platform.UPWORK,
            sent_date=date.today(),
        )
        from apps.proposals.services import DuplicateCheckService

        result = DuplicateCheckService.check_duplicate(
            user, client_model, Platform.UPWORK
        )
        assert result.is_duplicate is True


@pytest.mark.django_db
class TestExportAPIViews:
    def test_csv_export(self, user, client_model, authed_client):
        Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        from apps.exports.services import generate_proposals_csv

        csv_data = generate_proposals_csv(user)
        assert "Test Proposal" in csv_data

    def test_json_export(self, user, client_model, authed_client):
        Proposal.objects.create(
            owner=user,
            title="Test Proposal",
            client=client_model,
            amount=Decimal("1000"),
            status=ProposalStatus.DRAFT,
        )
        from apps.exports.services import generate_proposals_json

        json_data = generate_proposals_json(user)
        assert "Test Proposal" in json_data


@pytest.mark.django_db
class TestWebhookAPI:
    def test_webhook_without_signature(self, db):
        request = type("Request")()
        request.headers = {}
        request.body = b'{"event_type": "test"}'
        request.data = {"event_type": "test", "proposal_id": 1}

        response = webhook_proposal_events(request)
        assert response.status_code == 200
        assert response.data["status"] == "received"
