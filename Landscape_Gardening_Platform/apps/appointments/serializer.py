from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_duration_hours = serializers.IntegerField(source="service.duration_hours", read_only=True)
    team_member_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "client_name",
            "service",
            "service_name",
            "service_duration_hours",
            "assigned_team_member",
            "team_member_name",
            "scheduled_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]

    def get_team_member_name(self, obj):
        if not obj.assigned_team_member:
            return None
        return str(obj.assigned_team_member)


class AppointmentRequestSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    scheduled_date = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True)