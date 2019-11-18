import calendar
from datetime import datetime

from dateutil.parser import parse
from django.conf import settings
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
_year_param = openapi.Parameter(
    'year', openapi.IN_QUERY, description="year in format `%Y`", type=openapi.TYPE_STRING
)
_sustainability_response = openapi.Response(
    'sustainability dashboard for the selected period', SustainabilityDashboardSerializer
)


# noinspection PyMethodMayBeStatic
class SustainabilityDashboardViewSet(viewsets.ViewSet):
    """
    Generates sustainability stats (billable, non-billable, non-billable-cell-responsible hours) within date range.

    You should either use both `from` and `to` query params here or `year` query param.
    """

    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        manual_parameters=[_from_param, _to_param, _year_param], responses={200: _sustainability_response}
    )
    def list(self, request):
        from_ = request.query_params.get('from')
        to = request.query_params.get('to')
        year = request.query_params.get('year')
        if not (from_ and to) and not year:
            raise ValidationError("(`from` and `to`) or `year` query params are required.")

        if year:
            year_date = parse(year)
            from_ = year_date.replace(month=1, day=1).strftime(settings.JIRA_API_DATE_FORMAT)
            today = datetime.today()
            last_day_of_month = calendar.monthrange(today.year, today.month)[1]
            current_end_date = today.replace(day=last_day_of_month)
            to = min(current_end_date, year_date.replace(month=12, day=31)).strftime(settings.JIRA_API_DATE_FORMAT)
            dashboard = SustainabilityDashboard(from_, to, budgets=True)
        else:
            dashboard = SustainabilityDashboard(from_, to)
        serializer = SustainabilityDashboardSerializer(dashboard)
        return Response(serializer.data)
