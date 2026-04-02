import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_message(record):
    body = json.loads(record["body"])
    if "Message" in body:
        return json.loads(body["Message"])
    return body


def lambda_handler(event, context):
    failures = []

    for record in event.get("Records", []):
        try:
            message = extract_message(record)
            logger.info("Sending reminder: %s", message)

            appointment_id = message["appointment_id"]
            client_id = message["client_id"]
            service = message["service"]
            scheduled_time = message["scheduled_time"]

            logger.info(
                "Reminder sent to client %s for appointment %s (%s at %s)",
                client_id,
                appointment_id,
                service,
                scheduled_time,
            )

        except Exception:
            logger.exception("Failed to process reminder record")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}