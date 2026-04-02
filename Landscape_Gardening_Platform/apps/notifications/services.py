from django.utils import timezone
from .models import Notification


def send_notification(*, appointment, recipient, subject, message, channel="email"):
    notification = Notification.objects.create(
        appointment=appointment,
        recipient=recipient,
        subject=subject,
        message=message,
        channel=channel,
        status="pending",
    )

    # Real implementation would call email/SMS provider here.
    notification.status = "sent"
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at"])

    return notification