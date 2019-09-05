import http

from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.response import Response

from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.models import Dashboard
from sprints.dashboard.serializers import (
    CellSerializer,
    DashboardSerializer,
)
from sprints.dashboard.tasks import (
    complete_sprint,
    upload_spillovers_task,
)
from sprints.dashboard.utils import (
    get_cells,
)


# noinspection PyMethodMayBeStatic
class CellViewSet(viewsets.ViewSet):
    """
    Lists all available cells.
    GET /dashboard/cells/
    """

    permission_classes = (permissions.IsAuthenticated,)

    def list(self, _request):
        with connect_to_jira() as conn:
            cells = get_cells(conn)
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
        with connect_to_jira() as conn:
            dashboard = Dashboard(board_id, conn)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)


class SpilloverViewSet(viewsets.ViewSet):
    """
    Invokes task for uploading spillovers.
    POST /dashboard/spillovers
    """
    permission_classes = (permissions.IsAdminUser,)

    # noinspection PyMethodMayBeStatic
    def create(self, _request):
        upload_spillovers_task.delay()
        return Response(data='', status=http.HTTPStatus.OK)


class CompleteSprintViewSet(viewsets.ViewSet):
    """
    Invokes task for uploading spillovers and ending the sprints.
    POST /dashboard/end_sprint
    """
    permission_classes = (permissions.IsAdminUser,)

    # noinspection PyMethodMayBeStatic
    def create(self, request):
        board_id = int(request.query_params.get('board_id'))
        complete_sprint.delay(board_id)
        return Response(data='', status=http.HTTPStatus.OK)
