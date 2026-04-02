from django.urls import path,include
from . import views
from apps.appointments import views as appointment_views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path("api/appointments/", include("apps.appointments.urls")),
]
