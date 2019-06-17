from rest_framework import serializers

from sprints.dashboard.helpers import Cell, DashboardRow


class CellSerializer(serializers.Serializer):
    """Serializer for cells."""
    name = serializers.CharField(max_length=256)

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
    remaining_time = serializers.IntegerField()

    def get_name(self, obj: DashboardRow):
        return obj.user.displayName if obj.user else "Unassigned"

    def create(self, validated_data):
        raise NotImplementedError("This method is not allowed.")

    def update(self, instance, validated_data):
        raise NotImplementedError("This method is not allowed.")


class DashboardSerializer(serializers.Serializer):
    """Serializer for the dashboard."""
    rows = DashboardRowSerializer(many=True)
    cell = serializers.CharField(max_length=256, source='project')
    future_sprint = serializers.CharField(max_length=256, source='future_sprint_name')

    def create(self, validated_data):
        raise NotImplementedError("This method is not allowed.")

    def update(self, instance, validated_data):
        raise NotImplementedError("This method is not allowed.")
