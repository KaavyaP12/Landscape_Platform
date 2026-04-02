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
            logger.info("Processing weather message: %s", message)

            location = message.get("location", "").lower()

            risky_locations = {"manchester", "glasgow"}
            if location in risky_locations:
                logger.warning(
                    "Weather alert for appointment %s at %s",
                    message["appointment_id"],
                    location,
                )
            else:
                logger.info(
                    "Weather safe for appointment %s",
                    message["appointment_id"],
                )

        except Exception:
            logger.exception("Failed to process weather record")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}