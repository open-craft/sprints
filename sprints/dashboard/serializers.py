from rest_framework import serializers

from sprints.dashboard.models import (
    Dashboard,
    DashboardIssue,
    DashboardRow,
)


# noinspection PyAbstractClass
class CellSerializer(serializers.Serializer):
    """Serializer for cells."""
    name = serializers.CharField(max_length=256)
    board_id = serializers.IntegerField()


# noinspection PyAbstractClass
class DashboardIssueSerializer(serializers.Serializer):
    """Serializer for dashboard issue."""
    key = serializers.CharField()
    summary = serializers.CharField()
    account = serializers.CharField()
    assignee = serializers.SerializerMethodField()
    reviewer_1 = serializers.SerializerMethodField()
    current_sprint = serializers.BooleanField()
    is_epic = serializers.BooleanField()
    status = serializers.CharField()
    assignee_time = serializers.SerializerMethodField()
    review_time = serializers.IntegerField()

    # noinspection PyMethodMayBeStatic
    def get_assignee(self, obj: DashboardIssue):
        return obj.assignee.displayName

    # noinspection PyMethodMayBeStatic
    def get_reviewer_1(self, obj: DashboardIssue):
        return obj.reviewer_1.displayName

    # noinspection PyMethodMayBeStatic
    def get_assignee_time(self, obj: DashboardIssue):
        """Aggregates assignee, recurring and epic management time for easier data reading."""
        return obj.assignee_time + obj.recurring_time + obj.epic_management_time  # type: ignore


# noinspection PyAbstractClass
class DashboardRowSerializer(serializers.Serializer):
    """Serializer for dashboard row."""
    name = serializers.SerializerMethodField()
    current_remaining_assignee_time = serializers.IntegerField()
    current_remaining_review_time = serializers.IntegerField()
    current_remaining_upstream_time = serializers.IntegerField()
    future_assignee_time = serializers.IntegerField()
    future_review_time = serializers.IntegerField()
    future_epic_management_time = serializers.IntegerField()
    committed_time = serializers.IntegerField()
    goal_time = serializers.IntegerField()
    current_unestimated = DashboardIssueSerializer(many=True)
    future_unestimated = DashboardIssueSerializer(many=True)
    remaining_time = serializers.IntegerField()
    vacation_time = serializers.IntegerField()

    # noinspection PyMethodMayBeStatic
    def get_name(self, obj: DashboardRow):
        return obj.user.displayName


# noinspection PyAbstractClass
class DashboardSerializer(serializers.Serializer):
    """Serializer for the dashboard."""
    rows = DashboardRowSerializer(many=True)
    issues = DashboardIssueSerializer(many=True)
    future_sprint = serializers.SerializerMethodField()

    # noinspection PyMethodMayBeStatic
    def get_future_sprint(self, obj: Dashboard):
        return obj.cell_future_sprint.name
