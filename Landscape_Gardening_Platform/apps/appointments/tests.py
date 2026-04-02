from django.test import TestCase
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from apps.clients.models import Client
from apps.services.models import Service
from apps.team.models import TeamMember
from apps.notifications.models import Notification
from apps.appointments.models import Appointment, DomainEvent
from apps.appointments.event_processor import process_pending_events
from apps.appointments.services import request_appointment

# Create your tests here.
class AppointmentWorkflowTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="John Carter",
            email="john@example.com",
            phone="07111111111",
            address="14 Rosewood Drive, London",
        )

        self.service = Service.objects.create(
            name="Lawn Mowing",
            description="Outdoor mowing service",
            base_price=45.00,
            duration_hours=2,
            is_active=True,
            is_outdoor=True,
            priority="medium",
        )

        self.user = User.objects.create_user(
            username="gardener1",
            email="gardener1@example.com",
            password="Test1234",
        )

        self.team_member = TeamMember.objects.create(
            user=self.user,
            is_available=True,
        )
        self.team_member.specialties.add(self.service)

    def test_request_appointment_creates_domain_event(self):
        appointment = request_appointment(
            client_id=self.client_obj.id,
            service_id=self.service.id,
            scheduled_date=timezone.now() + timedelta(hours=2),
            notes="Test request",
        )

        self.assertEqual(appointment.status, "requested")
        self.assertEqual(DomainEvent.objects.filter(event_type="AppointmentRequested").count(), 1)

    def test_requested_appointment_gets_scheduled_when_weather_and_team_are_ok(self):
        appointment = request_appointment(
            client_id=self.client_obj.id,
            service_id=self.service.id,
            scheduled_date=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
            notes="Morning slot",
        )

        process_pending_events(batch_size=10)
        process_pending_events(batch_size=10)

        appointment.refresh_from_db()

        self.assertEqual(appointment.status, "scheduled")
        self.assertIsNotNone(appointment.assigned_team_member)
        self.assertEqual(Notification.objects.count(), 2)

    def test_requested_appointment_is_weather_blocked_for_late_outdoor_slot(self):
        appointment = request_appointment(
            client_id=self.client_obj.id,
            service_id=self.service.id,
            scheduled_date=timezone.now().replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=1),
            notes="Late slot",
        )

        process_pending_events(batch_size=10)
        appointment.refresh_from_db()

        self.assertEqual(appointment.status, "weather_blocked")

    def test_requested_appointment_is_team_unavailable_when_no_matching_team_exists(self):
        self.team_member.specialties.clear()

        appointment = request_appointment(
            client_id=self.client_obj.id,
            service_id=self.service.id,
            scheduled_date=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
            notes="No team available",
        )

        process_pending_events(batch_size=10)
        appointment.refresh_from_db()

        self.assertEqual(appointment.status, "team_unavailable")