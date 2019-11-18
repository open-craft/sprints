from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sprints.sustainability.models import SustainabilityDashboard
from sprints.sustainability.serializers import SustainabilityDashboardSerializer

_from_param = openapi.Parameter(
    'from', openapi.IN_QUERY, description="start date in format `%Y-%M-%d`", type=openapi.TYPE_STRING
)
_to_param = openapi.Parameter(
    'to', openapi.IN_QUERY, description="end date in format `%Y-%M-%d`", type=openapi.TYPE_STRING
)
_sustainability_response = openapi.Response(
    'sustainability dashboard for the selected period', SustainabilityDashboardSerializer
)


# noinspection PyMethodMayBeStatic
class SustainabilityDashboardViewSet(viewsets.ViewSet):
    """
    Generates sustainability stats (billable, non-billable, non-billable-cell-responsible hours) within date range.

    You should either use both `from` and `to` query params here.
    """

    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        manual_parameters=[_from_param, _to_param], responses={200: _sustainability_response}
    )
    def list(self, request):
        from_ = request.query_params.get('from')
        to = request.query_params.get('to')
        if not (from_ and to):
            raise ValidationError("`from` and `to` query params are required.")

        dashboard = SustainabilityDashboard(from_, to)
        serializer = SustainabilityDashboardSerializer(dashboard)
        return Response(serializer.data)
