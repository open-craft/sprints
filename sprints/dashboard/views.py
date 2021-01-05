import http
from datetime import datetime
from typing import (
    Tuple,
)

from dateutil.parser import parse
from django.conf import settings
from django.core.cache import cache
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import (
    permissions,
    viewsets,
)
from rest_framework.exceptions import PermissionDenied
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
    get_current_sprint_end_date,
    get_cell_member_roles,
    NoRolesFoundException,
)

_cache_param = openapi.Parameter(
    'cache', openapi.IN_QUERY, description="should use cached results?", type=openapi.TYPE_BOOLEAN
)
_cell_response = openapi.Response('list of the cells', CellSerializer)
_dashboard_response = openapi.Response('sprint planning dashboard', DashboardSerializer)
_task_scheduled_response = openapi.Response("task scheduled")
_can_complete_sprint = openapi.Response("can complete sprint")
_cannot_complete_sprint = openapi.Response("cannot complete sprint")


# noinspection PyMethodMayBeStatic
class DashboardViewSet(viewsets.ViewSet):
    """
    Handles listing, retrieving and adding new sprint for cell boards.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: _cell_response})
    def list(self, _request):
        """Lists all available cells."""
        with connect_to_jira() as conn:
            cells = get_cells(conn)
        serializer = CellSerializer(cells, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(manual_parameters=[_cache_param], responses={200: _dashboard_response})
    def retrieve(self, request, pk=None):
        """Generates a specified cell's board."""
        use_cache = bool(request.query_params.get('cache', False))
        data = cache.get(pk) if use_cache else None

        if not data:
            with connect_to_jira() as conn:
                dashboard = Dashboard(int(pk), conn)
                data = DashboardSerializer(dashboard).data
                cache.set(pk, data, settings.CACHE_SPRINT_TIMEOUT_ONE_TIME)
        return Response(data)

    @swagger_auto_schema(responses={200: _task_scheduled_response})
    def update(self, _request, pk=None):
        """Invokes task for creating the next sprint for the chosen cell."""
        create_next_sprint_task.delay(int(pk))
        return Response(data='', status=http.HTTPStatus.OK)


# noinspection PyMethodMayBeStatic
class CompleteSprintViewSet(viewsets.ViewSet):
    """
    Handles ending the sprint for the chosen cell.
    """
    permission_classes = (permissions.IsAdminUser,)

    @staticmethod
    def can_end_sprint(board_id: int, acquire_lock: bool = False) -> Tuple[bool, str]:
        """
        Checks if the sprint can be closed now. If it cannot be closed, this returns the reason. There are 2 conditions:
        1. The current day is the last day of the current sprint.
        2. The lock for ending the sprint is not acquired.

        Acquire a lock for a day, if `acquire_lock` specified.
        """
        end_date = parse(get_current_sprint_end_date('cell', str(board_id)))
        if datetime.now() < end_date and False: #TODO: REMOVE
            return False, "The current day is not the last day of the current sprint."

        if settings.FEATURE_CELL_ROLES:
            try:
                get_cell_member_roles(raise_exception=True)
            except NoRolesFoundException as msg:
                return False, str(msg)

        if (acquire_lock and not cache.add(
            f'{settings.CACHE_SPRINT_END_LOCK}{board_id}', True, settings.CACHE_SPRINT_END_LOCK_TIMEOUT_SECONDS
        )) or (not acquire_lock and cache.get(f'{settings.CACHE_SPRINT_END_LOCK}{board_id}', False)):
            return False, "The completion task is already running or hasn't been completed successfully."

        return True, ''

    @swagger_auto_schema(responses={200: _can_complete_sprint, 403: _cannot_complete_sprint})
    def retrieve(self, _request, pk=None):
        """Checks if the sprint can be closed now. Otherwise returns proper error message."""
        status, error_message = self.can_end_sprint(pk)
        if not status:
            raise PermissionDenied(detail=error_message)
        return Response(data='', status=http.HTTPStatus.OK)

    @swagger_auto_schema(responses={200: _task_scheduled_response, 403: _cannot_complete_sprint})
    def update(self, _request, pk=None):
        """
        Invokes task for uploading spillovers and ending the sprint for the chosen cell.

        Sets a lock in the cache, so it won't be possible to schedule the sprint completion task twice for one cell.
        We want to set it here (instead of doing it inside the task) to avoid race conditions.
        """
        status, error_message = self.can_end_sprint(pk, acquire_lock=True)
        if not status:
            raise PermissionDenied(detail=error_message)

        complete_sprint_task.delay(int(pk))
        return Response(data='', status=http.HTTPStatus.OK)
