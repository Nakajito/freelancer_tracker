"""Tests for send_digest management command with i18n/language support."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.followups.models import FollowUp
from apps.proposals.models import Client, Proposal, ProposalStatus

User = get_user_model()


@pytest.fixture
def en_user(db):
    return User.objects.create_user(
        username="en_user",
        email="en@example.com",
        password="pass",
        language_preference="en",
    )


@pytest.fixture
def es_user(db):
    return User.objects.create_user(
        username="es_user",
        email="es@example.com",
        password="pass",
        language_preference="es",
    )


@pytest.fixture
def proposal_with_followup(db, en_user):
    client_obj = Client.objects.create(owner=en_user, name="Test Client")
    proposal = Proposal.objects.create(
        owner=en_user,
        title="Test Proposal",
        client=client_obj,
        status=ProposalStatus.SENT,
        amount=Decimal("1000.00"),
        sent_date=date.today(),
    )
    FollowUp.objects.create(
        proposal=proposal,
        due_date=date.today() - timedelta(days=1),
        notes="Call client",
        completed=False,
    )
    return proposal


@pytest.fixture
def es_proposal_with_followup(db, es_user):
    client_obj = Client.objects.create(owner=es_user, name="Cliente Test")
    proposal = Proposal.objects.create(
        owner=es_user,
        title="Propuesta Test",
        client=client_obj,
        status=ProposalStatus.SENT,
        amount=Decimal("2000.00"),
        sent_date=date.today(),
    )
    FollowUp.objects.create(
        proposal=proposal,
        due_date=date.today() - timedelta(days=1),
        notes="Llamar al cliente",
        completed=False,
    )
    return proposal


@pytest.mark.django_db
class TestSendDigestLanguageOverride:
    def test_digest_renders_in_english_for_en_user(
        self, en_user, proposal_with_followup
    ):
        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest")

        assert mock_send.called
        call_kwargs = mock_send.call_args
        message = (
            call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs["message"]
        )
        assert "Hi" in message
        assert "Overdue Follow-ups" in message

    def test_digest_renders_in_spanish_for_es_user(
        self, es_user, es_proposal_with_followup
    ):
        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest")

        assert mock_send.called
        call_kwargs = mock_send.call_args
        message = (
            call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs["message"]
        )
        assert "Hola" in message
        assert "Seguimientos vencidos" in message

    def test_dry_run_does_not_send_email(self, en_user, proposal_with_followup):
        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest", "--dry-run")

        mock_send.assert_not_called()

    def test_no_email_sent_when_no_followups(self, en_user):
        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest")

        mock_send.assert_not_called()

    def test_digest_email_sent_to_correct_address(
        self, en_user, proposal_with_followup
    ):
        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest")

        assert mock_send.called
        call_kwargs = mock_send.call_args
        recipient_list = (
            call_kwargs.args[3]
            if len(call_kwargs.args) > 3
            else call_kwargs.kwargs["recipient_list"]
        )
        assert en_user.email in recipient_list

    def test_default_language_used_when_preference_missing(
        self, db, proposal_with_followup
    ):
        """User with no explicit language_preference defaults to 'en'."""
        user = proposal_with_followup.owner
        # Simulate missing language_preference by blanking it
        user.language_preference = ""
        user.save()

        with patch("apps.core.management.commands.send_digest.send_mail") as mock_send:
            call_command("send_digest")

        assert mock_send.called
        call_kwargs = mock_send.call_args
        # Should not crash and should still render template content
        assert (
            "Digest" in call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs.kwargs["subject"]
        )
