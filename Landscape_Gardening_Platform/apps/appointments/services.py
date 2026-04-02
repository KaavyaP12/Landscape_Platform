from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from apps.clients.models import Client
from apps.services.models import Service
from apps.team.models import TeamMember
from apps.notifications.services import send_notification

from .models import Appointment, DomainEvent
from .weather import check_weather_for_appointment


def publish_event(*, event_type, aggregate_type, aggregate_id, payload):
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )


def has_time_conflict(team_member, scheduled_date, duration_hours, exclude_appointment_id=None):
    requested_start = scheduled_date
    requested_end = scheduled_date + timedelta(hours=duration_hours)

    existing_appointments = (
        Appointment.objects.select_related("service")
        .filter(
            assigned_team_member=team_member,
            status__in=["scheduled", "in_progress"],
        )
    )

    if exclude_appointment_id:
        existing_appointments = existing_appointments.exclude(id=exclude_appointment_id)

    for appointment in existing_appointments:
        existing_start = appointment.scheduled_date
        existing_end = existing_start + timedelta(hours=appointment.service.duration_hours)

        overlaps = requested_start < existing_end and requested_end > existing_start
        if overlaps:
            return True

    return False


def find_available_team_member(service, scheduled_date, exclude_team_member_id=None, exclude_appointment_id=None):
    candidates = (
        TeamMember.objects.filter(
            is_available=True,   # general availability only: leave/sick/inactive
            specialties=service,
        )
        .select_related("user")
        .distinct()
    )

    if exclude_team_member_id:
        candidates = candidates.exclude(id=exclude_team_member_id)

    for member in candidates:
        if not has_time_conflict(
            team_member=member,
            scheduled_date=scheduled_date,
            duration_hours=service.duration_hours,
            exclude_appointment_id=exclude_appointment_id,
        ):
            return member

    return None


@transaction.atomic
def create_appointment_with_validation(*, client_id, service_id, scheduled_date, notes=""):
    """
    Synchronous booking:
    - validate client/service/time/weather/team availability
    - create appointment only if all checks pass
    - publish events only AFTER successful booking
    """
    if scheduled_date <= timezone.now():
        raise ValueError("Appointment must be scheduled in the future.")

    client = Client.objects.filter(id=client_id).first()
    if not client:
        raise ValueError("Client not found.")

    service = Service.objects.filter(id=service_id, is_active=True).first()
    if not service:
        raise ValueError("Active service not found.")

    class TempAppointment:
        pass

    temp_appointment = TempAppointment()
    temp_appointment.service = service
    temp_appointment.scheduled_date = scheduled_date

    weather = check_weather_for_appointment(temp_appointment)
    if not weather["safe"]:
        raise ValueError(f"Appointment cannot be scheduled due to weather: {weather['reason']}")

    team_member = find_available_team_member(service, scheduled_date)
    if not team_member:
        raise ValueError("No team member is available at this time.")

    appointment = Appointment.objects.create(
        client=client,
        service=service,
        assigned_team_member=team_member,
        scheduled_date=scheduled_date,
        notes=notes,
        status="scheduled",
    )

    # Event-driven side effects after successful booking
    publish_event(
        event_type="AppointmentScheduled",
        aggregate_type="Appointment",
        aggregate_id=appointment.id,
        payload={
            "appointment_id": appointment.id,
            "team_member_id": team_member.id,
        },
    )

    publish_event(
        event_type="ClientConfirmationRequested",
        aggregate_type="Appointment",
        aggregate_id=appointment.id,
        payload={"appointment_id": appointment.id},
    )

    publish_event(
        event_type="TeamNotificationRequested",
        aggregate_type="Appointment",
        aggregate_id=appointment.id,
        payload={"appointment_id": appointment.id},
    )

    return appointment


@transaction.atomic
def handle_client_confirmation_requested(event):
    appointment = (
        Appointment.objects.select_related("client", "service", "assigned_team_member__user")
        .filter(id=event.payload["appointment_id"])
        .first()
    )
    if not appointment:
        raise ValueError("Appointment does not exist.")

    send_notification(
        appointment=appointment,
        recipient=appointment.client.email,
        subject="Appointment Confirmed",
        message=(
            f"Your appointment for {appointment.service.name} is confirmed for "
            f"{appointment.scheduled_date}."
        ),
        channel="email",
    )


@transaction.atomic
def handle_team_notification_requested(event):
    appointment = (
        Appointment.objects.select_related("client", "service", "assigned_team_member__user")
        .filter(id=event.payload["appointment_id"])
        .first()
    )
    if not appointment:
        raise ValueError("Appointment does not exist.")

    if not appointment.assigned_team_member:
        raise ValueError("No team member assigned for this appointment.")

    recipient = (
        appointment.assigned_team_member.user.email
        or appointment.assigned_team_member.user.username
    )

    send_notification(
        appointment=appointment,
        recipient=recipient,
        subject="New Appointment Assigned",
        message=(
            f"You have been assigned to {appointment.service.name} for "
            f"{appointment.client.name} on {appointment.scheduled_date}."
        ),
        channel="internal",
    )


@transaction.atomic
def handle_team_member_unavailable(event):
    """
    Reassign future appointments for a team member who becomes unavailable.
    If replacement is found, keep appointment scheduled.
    If not, mark as team_unavailable and publish follow-up event.
    """
    team_member_id = event.payload["team_member_id"]

    appointments = Appointment.objects.select_related("service", "client").filter(
        assigned_team_member_id=team_member_id,
        status="scheduled",
        scheduled_date__gte=timezone.now(),
    )

    for appointment in appointments:
        replacement = find_available_team_member(
            service=appointment.service,
            scheduled_date=appointment.scheduled_date,
            exclude_team_member_id=team_member_id,
            exclude_appointment_id=appointment.id,
        )

        if replacement:
            appointment.assigned_team_member = replacement
            appointment.status = "scheduled"
            appointment.save(update_fields=["assigned_team_member", "status", "updated_at"])

            publish_event(
                event_type="AppointmentReassigned",
                aggregate_type="Appointment",
                aggregate_id=appointment.id,
                payload={
                    "appointment_id": appointment.id,
                    "new_team_member_id": replacement.id,
                },
            )

            publish_event(
                event_type="ClientConfirmationRequested",
                aggregate_type="Appointment",
                aggregate_id=appointment.id,
                payload={"appointment_id": appointment.id},
            )

            publish_event(
                event_type="TeamNotificationRequested",
                aggregate_type="Appointment",
                aggregate_id=appointment.id,
                payload={"appointment_id": appointment.id},
            )
        else:
            appointment.assigned_team_member = None
            appointment.status = "team_unavailable"
            appointment.save(update_fields=["assigned_team_member", "status", "updated_at"])

            publish_event(
                event_type="AppointmentTeamUnavailable",
                aggregate_type="Appointment",
                aggregate_id=appointment.id,
                payload={"appointment_id": appointment.id},
            )


@transaction.atomic
def handle_weather_changed(event):
    """
    Re-check weather for an already scheduled appointment.
    If unsafe, mark weather_blocked and publish follow-up event.
    """
    appointment_id = event.payload["appointment_id"]

    appointment = (
        Appointment.objects.select_related("service", "client", "assigned_team_member__user")
        .filter(id=appointment_id)
        .first()
    )
    if not appointment:
        raise ValueError("Appointment does not exist.")

    weather = check_weather_for_appointment(appointment)
    if not weather["safe"]:
        appointment.status = "weather_blocked"
        appointment.save(update_fields=["status", "updated_at"])

        publish_event(
            event_type="AppointmentWeatherBlocked",
            aggregate_type="Appointment",
            aggregate_id=appointment.id,
            payload={
                "appointment_id": appointment.id,
                "reason": weather["reason"],
            },
        )


@transaction.atomic
def handle_appointment_team_unavailable(event):
    appointment = (
        Appointment.objects.select_related("client", "service")
        .filter(id=event.payload["appointment_id"])
        .first()
    )
    if not appointment:
        raise ValueError("Appointment does not exist.")

    send_notification(
        appointment=appointment,
        recipient=appointment.client.email,
        subject="Appointment Needs Rescheduling",
        message=(
            f"We could not confirm a team member for your appointment for "
            f"{appointment.service.name} on {appointment.scheduled_date}. "
            f"Our team will contact you to reschedule."
        ),
        channel="email",
    )


@transaction.atomic
def handle_appointment_weather_blocked(event):
    appointment = (
        Appointment.objects.select_related("client", "service")
        .filter(id=event.payload["appointment_id"])
        .first()
    )
    if not appointment:
        raise ValueError("Appointment does not exist.")

    reason = event.payload.get("reason", "weather risk")

    send_notification(
        appointment=appointment,
        recipient=appointment.client.email,
        subject="Appointment Blocked by Weather",
        message=(
            f"Your appointment for {appointment.service.name} on "
            f"{appointment.scheduled_date} is currently blocked due to {reason}."
        ),
        channel="email",
    )


EVENT_HANDLERS = {
    "ClientConfirmationRequested": handle_client_confirmation_requested,
    "TeamNotificationRequested": handle_team_notification_requested,
    "TeamMemberUnavailable": handle_team_member_unavailable,
    "WeatherChanged": handle_weather_changed,
    "AppointmentTeamUnavailable": handle_appointment_team_unavailable,
    "AppointmentWeatherBlocked": handle_appointment_weather_blocked,
}