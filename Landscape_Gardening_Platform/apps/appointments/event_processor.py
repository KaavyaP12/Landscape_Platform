from django.utils import timezone
from .models import DomainEvent
from .services import EVENT_HANDLERS


MAX_RETRIES = 3


def process_pending_events(batch_size=20):
    events = DomainEvent.objects.filter(
        status__in=["pending", "failed"],
        retry_count__lt=MAX_RETRIES,
    )[:batch_size]

    processed_count = 0

    for event in events:
        handler = EVENT_HANDLERS.get(event.event_type)

        if not handler:
            event.status = "failed"
            event.retry_count += 1
            event.error_message = f"No handler configured for {event.event_type}"
            event.save(update_fields=["status", "retry_count", "error_message"])
            continue

        try:
            handler(event)
            event.status = "processed"
            event.processed_at = timezone.now()
            event.error_message = ""
            event.save(update_fields=["status", "processed_at", "error_message"])
            processed_count += 1
        except Exception as exc:
            event.status = "failed"
            event.retry_count += 1
            event.error_message = str(exc)
            event.save(update_fields=["status", "retry_count", "error_message"])

    return processed_count