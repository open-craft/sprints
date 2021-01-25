from rest_framework import serializers


# noinspection PyAbstractClass
class SustainabilityAccountSerializer(serializers.Serializer):
    """Serializer for Accounts."""

    name = serializers.CharField()
    overall = serializers.FloatField()
    by_project = serializers.DictField()
    by_person = serializers.DictField()
    ytd_overall = serializers.FloatField()
    ytd_by_project = serializers.DictField()
    ytd_by_person = serializers.DictField()
    budgets = serializers.DictField()
    period_goal = serializers.FloatField()
    ytd_goal = serializers.FloatField()
    next_sprint_goal = serializers.FloatField()


# noinspection PyAbstractClass
class SustainabilityDashboardSerializer(serializers.Serializer):
    """Serializer for Sustainability Dashboard."""

    billable_accounts = SustainabilityAccountSerializer(many=True)
    non_billable_accounts = SustainabilityAccountSerializer(many=True)
    non_billable_responsible_accounts = SustainabilityAccountSerializer(many=True)
