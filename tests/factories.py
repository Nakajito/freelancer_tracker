import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, Tag


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(
        lambda obj: f"{obj.username}@freelancer-tracker.dabg.dev"
    )
    password = factory.PostGenerationMethodCall("set_password", "password123")


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client

    name = factory.Sequence(lambda n: f"Client {n}")
    owner = factory.SubFactory(UserFactory)


class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")
    owner = factory.SubFactory(UserFactory)


class ProposalFactory(DjangoModelFactory):
    class Meta:
        model = Proposal

    title = factory.Sequence(lambda n: f"Proposal {n}")
    platform = Platform.UPWORK
    client = factory.SubFactory(ClientFactory)
    status = ProposalStatus.DRAFT
    amount = 1000
    owner = factory.LazyAttribute(lambda obj: obj.client.owner)
