from django.contrib import admin
from .models import Notification

# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "appointment",
        "recipient",
        "channel",
        "status",
        "sent_at",
        "created_at",
    )
    list_filter = ("channel", "status", "created_at")
    search_fields = ("recipient", "subject", "message")