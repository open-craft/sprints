from rest_framework import serializers

from sprints.dashboard.helpers import (
    Cell,
    Dashboard,
    DashboardRow,
)


class CellSerializer(serializers.Serializer):
    """Serializer for cells."""
    name = serializers.CharField(max_length=256)
    board_id = serializers.IntegerField()

    def create(self, validated_data):
        return Cell(**validated_data)

    def update(self, instance, validated_data):
        raise NotImplementedError("This method is not allowed.")


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
    current_invalid = serializers.ListField()
    future_invalid = serializers.ListField()
    remaining_time = serializers.IntegerField()

    def get_name(self, obj: DashboardRow):
        try:
            return obj.user.displayName if obj.user else "Unassigned"
        except AttributeError:
            return obj.user

    def create(self, validated_data):
        raise NotImplementedError("This method is not allowed.")

    def update(self, instance, validated_data):
        raise NotImplementedError("This method is not allowed.")


class DashboardSerializer(serializers.Serializer):
    """Serializer for the dashboard."""
    rows = DashboardRowSerializer(many=True)
    future_sprint = serializers.SerializerMethodField()

    def get_future_sprint(self, obj: Dashboard):
        return obj.future_sprint.name

    def create(self, validated_data):
        raise NotImplementedError("This method is not allowed.")

    def update(self, instance, validated_data):
        raise NotImplementedError("This method is not allowed.")
