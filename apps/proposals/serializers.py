from rest_framework import serializers

from apps.proposals.models import Proposal


class DuplicateCheckSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    platform = serializers.CharField()
    days = serializers.IntegerField(default=30, required=False)


class DuplicateCheckResultSerializer(serializers.Serializer):
    is_duplicate = serializers.BooleanField()
    existing_proposals = serializers.ListField(child=serializers.DictField())


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = [
            "id",
            "title",
            "platform",
            "client",
            "proposal_text",
            "amount",
            "status",
            "sent_date",
            "expected_response_date",
            "actual_response_date",
            "job_url",
            "proposal_url",
            "tags",
            "paid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProposalExportSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Proposal
        fields = [
            "id",
            "title",
            "client_name",
            "platform",
            "status",
            "amount",
            "sent_date",
            "expected_response_date",
            "actual_response_date",
            "paid",
        ]
