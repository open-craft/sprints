from rest_framework import (
    viewsets,
    permissions,
)
from rest_framework.response import Response

from sprints.dashboard.helpers import (
    Dashboard,
    get_cells,
)
from sprints.dashboard.serializers import (
    CellSerializer,
    DashboardSerializer,
)


# noinspection PyMethodMayBeStatic
class CellViewSet(viewsets.ViewSet):
    """
    Lists all available cells.
    GET /dashboard/cells/
    """

    permission_classes = (permissions.IsAuthenticated,)

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
        - board_id: cell's board ID.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        board_id = int(request.query_params.get('board_id'))
        dashboard = Dashboard(board_id)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)
