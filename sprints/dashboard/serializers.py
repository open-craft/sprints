from jira import (
    User as JiraUser,
)
from rest_framework import serializers

from sprints.dashboard.models import (
    Dashboard,
    DashboardRow,
)


# noinspection PyAbstractClass
class CellSerializer(serializers.Serializer):
    """Serializer for cells."""
    name = serializers.CharField(max_length=256)
    board_id = serializers.IntegerField()


# noinspection PyAbstractClass
class DashboardRowSerializer(serializers.Serializer):
    """Serializer for dashboard rows."""
    name = serializers.SerializerMethodField()
    current_remaining_assignee_time = serializers.IntegerField()
    current_remaining_review_time = serializers.IntegerField()
    current_remaining_upstream_time = serializers.IntegerField()
    future_remaining_assignee_time = serializers.IntegerField()
    future_remaining_review_time = serializers.IntegerField()
    future_epic_management_time = serializers.IntegerField()
    committed_time = serializers.IntegerField()
    goal_time = serializers.IntegerField()
    current_unestimated = serializers.ListField()
    future_unestimated = serializers.ListField()
    remaining_time = serializers.IntegerField()

    # noinspection PyMethodMayBeStatic
    def get_name(self, obj: DashboardRow):
        if isinstance(obj.user, JiraUser):
            return obj.user.displayName
        elif obj.user:
            return "Unassigned"
        return obj.user


# noinspection PyAbstractClass
class DashboardSerializer(serializers.Serializer):
    """Serializer for the dashboard."""
    rows = DashboardRowSerializer(many=True)
    future_sprint = serializers.SerializerMethodField()

    # noinspection PyMethodMayBeStatic
    def get_future_sprint(self, obj: Dashboard):
        return obj.future_sprint.name
