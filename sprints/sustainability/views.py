from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sprints.dashboard.libs.jira import connect_to_jira
from sprints.sustainability.models import SustainabilityDashboard
from sprints.sustainability.serializers import SustainabilityDashboardSerializer


# noinspection PyMethodMayBeStatic
class SustainabilityDashboardViewSet(viewsets.ViewSet):
    """
    Generates sustainability stats (billable, non-billable, non-billable-cell-responsible hours) within date range.
    GET /sustainability/dashboard?from=<from_date>&to=<to_date>
    Query params:
        - from: start date in format `%Y-%M-%d`.
        - to: end date in format `%Y-%M-%d`.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        from_ = request.query_params.get('from')
        to = request.query_params.get('to')
        if not (from_ and to):
            raise ValidationError("`from` and `to` query params are required.")

        with connect_to_jira() as conn:
            dashboard = SustainabilityDashboard(conn, from_, to)
        serializer = SustainabilityDashboardSerializer(dashboard)
        return Response(serializer.data)
