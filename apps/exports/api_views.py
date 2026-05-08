import hashlib
import hmac

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_proposal_events(request):
    signature = request.headers.get("X-Signature", "")
    payload = request.body

    expected_signature = hmac.new(
        key=b"webhook-secret-key",
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if signature and not hmac.compare_digest(signature, expected_signature):
        return Response(
            {"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED
        )

    event_type = request.data.get("event_type", "")
    proposal_id = request.data.get("proposal_id")

    return Response(
        {
            "status": "received",
            "event_type": event_type,
            "proposal_id": proposal_id,
        }
    )
