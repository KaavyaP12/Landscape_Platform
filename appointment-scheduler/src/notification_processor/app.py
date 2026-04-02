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
            logger.info("Sending team notification: %s", message)

            logger.info(
                "Team notification sent for appointment %s: %s",
                message["appointment_id"],
                message["team_message"],
            )

        except Exception:
            logger.exception("Failed to process team notification record")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}