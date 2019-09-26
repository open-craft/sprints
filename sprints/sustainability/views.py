from datetime import datetime

from dateutil.parser import parse
from django.conf import settings
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
    OR
    GET /sustainability/dashboard?year=<year>
    Query params:
        - from: start date in format `%Y-%M-%d`.
        - to: end date in format `%Y-%M-%d`.
        - year: year in format `%Y`.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        from_ = request.query_params.get('from')
        to = request.query_params.get('to')
        year = request.query_params.get('year')
        if not (from_ and to) and not year:
            raise ValidationError("(`from` and `to`) or `year` query params are required.")

        with connect_to_jira() as conn:
            if year:
                year_date = parse(year)
                from_ = year_date.replace(month=1, day=1).strftime(settings.JIRA_API_DATE_FORMAT)
                to = min(datetime.today(), year_date.replace(month=12, day=31)).strftime(settings.JIRA_API_DATE_FORMAT)
                dashboard = SustainabilityDashboard(conn, from_, to, budgets=True)
            else:
                dashboard = SustainabilityDashboard(conn, from_, to)
        serializer = SustainabilityDashboardSerializer(dashboard)
        return Response(serializer.data)
