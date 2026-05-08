import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otheruser", email="other@example.com", password="otherpass123"
    )


@pytest.fixture
def authed_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def client_model(db, user):
    from apps.proposals.models import Client

    return Client.objects.create(owner=user, name="Test Client")


@pytest.fixture
def proposal(db, user, client_model):
    from apps.proposals.models import Proposal, ProposalStatus

    return Proposal.objects.create(
        owner=user,
        title="Test Proposal",
        client=client_model,
        status=ProposalStatus.DRAFT,
        amount=1000,
    )


@pytest.fixture
def accepted_proposal(db, user, client_model):
    from apps.proposals.models import Proposal, ProposalStatus
    from datetime import date

    return Proposal.objects.create(
        owner=user,
        title="Accepted Proposal",
        client=client_model,
        status=ProposalStatus.ACCEPTED,
        amount=2000,
        sent_date=date.today(),
    )
