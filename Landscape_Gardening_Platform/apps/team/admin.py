from django.contrib import admin
from .models import TeamMember

# Register your models here.
@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "is_available")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
    list_filter = ("is_available",)
    filter_horizontal = ("specialties",)