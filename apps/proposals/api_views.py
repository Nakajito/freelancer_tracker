"""DRF endpoints for proposal duplicate-check and exports."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.exports.services import CSVExporter
from apps.proposals.models import Client, Proposal
from apps.proposals.serializers import (
    DuplicateCheckResultSerializer,
    DuplicateCheckSerializer,
    ProposalExportSerializer,
)
from apps.proposals.services import DuplicateCheckService


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def duplicate_check(request):
    """Check whether the user already has a recent proposal for client+platform."""
    serializer = DuplicateCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    client_id = serializer.validated_data["client_id"]
    platform = serializer.validated_data["platform"]
    days = serializer.validated_data.get("days", 30)

    try:
        client = Client.objects.for_user(request.user).get(pk=client_id)
    except Client.DoesNotExist:
        return Response(
            {"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND
        )

    result = DuplicateCheckService.check_duplicate(
        owner=request.user,
        client=client,
        platform=platform,
        days=days,
    )

    result_serializer = DuplicateCheckResultSerializer(result)
    return Response(result_serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proposal_export_json(request):
    """Return all of the user's proposals as JSON."""
    proposals = (
        Proposal.objects.for_user(request.user).with_client().select_related("client")
    )
    serializer = ProposalExportSerializer(proposals, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proposal_export_csv(request):
    """Return all of the user's proposals as a CSV download."""
    proposals = (
        Proposal.objects.for_user(request.user).with_client().select_related("client")
    )
    generator = CSVExporter.export_proposals(proposals)
    response = HttpResponse(next(generator), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=proposals.csv"
    return response
