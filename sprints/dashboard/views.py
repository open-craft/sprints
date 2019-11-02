import http

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
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
    complete_sprint_task,
    create_next_sprint_task,
)
from sprints.dashboard.utils import (
    get_cells,
)

_board_id_param = openapi.Parameter(
    'board_id', openapi.IN_QUERY, description="cell's board ID", type=openapi.TYPE_INTEGER
)
_cell_response = openapi.Response('list of the cells', CellSerializer)
_dashboard_response = openapi.Response('sprint planning dashboard', DashboardSerializer)
_task_scheduled_response = openapi.Response("task scheduled")


# noinspection PyMethodMayBeStatic
class CellViewSet(viewsets.ViewSet):
    """
    Lists all available cells.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: _cell_response})
    def list(self, _request):
        with connect_to_jira() as conn:
            cells = get_cells(conn)
        serializer = CellSerializer(cells, many=True)
        return Response(serializer.data)


# noinspection PyMethodMayBeStatic
class DashboardViewSet(viewsets.ViewSet):
    """
    Generates a specified cell's board.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[_board_id_param], responses={200: _dashboard_response})
    def list(self, request):
        board_id = int(request.query_params.get('board_id'))
        with connect_to_jira() as conn:
            dashboard = Dashboard(board_id, conn)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)


# noinspection PyMethodMayBeStatic
class CreateNextSprintViewSet(viewsets.ViewSet):
    """
    Invokes task for creating the next sprint for the chosen cell.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[_board_id_param], responses={200: _task_scheduled_response})
    def create(self, request):
        board_id = int(request.query_params.get('board_id'))
        create_next_sprint_task.delay(board_id)
        return Response(data='', status=http.HTTPStatus.OK)


# noinspection PyMethodMayBeStatic
class CompleteSprintViewSet(viewsets.ViewSet):
    """
    Invokes task for uploading spillovers and ending the sprint for the chosen cell.
    """
    permission_classes = (permissions.IsAdminUser,)

    @swagger_auto_schema(manual_parameters=[_board_id_param], responses={200: _task_scheduled_response})
    def create(self, request):
        board_id = int(request.query_params.get('board_id'))
        complete_sprint_task.delay(board_id)
        return Response(data='', status=http.HTTPStatus.OK)
