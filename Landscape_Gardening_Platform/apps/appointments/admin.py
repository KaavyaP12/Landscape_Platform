from django.contrib import admin
from .models import Appointment, DomainEvent

# Register your models here.
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "service",
        "assigned_team_member",
        "scheduled_date",
        "status",
        "created_at",
    )
    list_filter = ("status", "scheduled_date", "created_at")
    search_fields = ("client__name", "service__name", "notes")


@admin.register(DomainEvent)
class DomainEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "status",
        "retry_count",
        "created_at",
        "processed_at",
    )
    list_filter = ("event_type", "status", "created_at")
    search_fields = ("event_type", "aggregate_type", "error_message")