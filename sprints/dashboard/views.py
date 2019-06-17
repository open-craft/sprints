from rest_framework import viewsets
from rest_framework.response import Response

from config.settings.base import JIRA_BOARD_ID
from sprints.dashboard.helpers import Dashboard, get_active_sprint, get_cells
from sprints.dashboard.serializers import CellSerializer, DashboardSerializer


# noinspection PyMethodMayBeStatic
class CellViewSet(viewsets.ViewSet):
    """
    Lists all available cells.
    GET /dashboard/cells/
    """

    # permission_classes = (permissions.IsAuthenticated,)  # FIXME: uncomment after finishing react auth

    def list(self, _request):
        cells = get_cells()
        serializer = CellSerializer(cells, many=True)
        return Response(serializer.data)


# noinspection PyMethodMayBeStatic
class DashboardViewSet(viewsets.ViewSet):
    """
    Generates a specified cell's board.
    GET /dashboard/dashboard
    Query params:
        - project: selected cell
        - board_od (optional): redundant if sprint numbers are the same for all cells
    """

    # permission_classes = (permissions.IsAuthenticated,)  # FIXME: uncomment after finishing react auth

    def list(self, request):
        project = request.query_params.get('project')
        board_id = int(request.query_params.get('board_id', JIRA_BOARD_ID))
        sprint = get_active_sprint(board_id)
        dashboard = Dashboard(project, sprint)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)
