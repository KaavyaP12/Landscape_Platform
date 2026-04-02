from django.contrib import admin
from .models import Service

# Register your models here.
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "duration_hours", "priority", "is_active", "is_outdoor")
    list_filter = ("priority", "is_active", "is_outdoor")
    search_fields = ("name", "description")