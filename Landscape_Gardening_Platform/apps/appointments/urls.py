from django.urls import path
from . import views

urlpatterns = [
    path("", views.appointment_list_api, name="appointment_list_api"),
    path("request/", views.appointment_request_api, name="appointment_request_api"),
    path("<int:appointment_id>/weather-change/", views.simulate_weather_change_api, name="simulate_weather_change_api"),
    path("team/<int:team_member_id>/unavailable/", views.simulate_team_unavailable_api, name="simulate_team_unavailable_api"),
]