import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client("sns")

WEATHER_ALERT_TOPIC_ARN = os.environ["WEATHER_ALERT_TOPIC_ARN"]
REMINDER_DUE_TOPIC_ARN = os.environ["REMINDER_DUE_TOPIC_ARN"]
TEAM_NOTIFICATION_TOPIC_ARN = os.environ["TEAM_NOTIFICATION_TOPIC_ARN"]


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
            logger.info("Processing appointment message: %s", message)

            appointment_id = message["appointment_id"]
            client_id = message["client_id"]
            service = message["service"]
            scheduled_time = message["scheduled_time"]
            is_outdoor = message.get("is_outdoor", False)

            if is_outdoor:
                sns.publish(
                    TopicArn=WEATHER_ALERT_TOPIC_ARN,
                    Subject="WeatherCheckRequired",
                    Message=json.dumps({
                        "appointment_id": appointment_id,
                        "location": message.get("location", ""),
                        "service": service,
                        "scheduled_time": scheduled_time,
                        "is_outdoor": True
                    })
                )

            sns.publish(
                TopicArn=REMINDER_DUE_TOPIC_ARN,
                Subject="ReminderDue",
                Message=json.dumps({
                    "appointment_id": appointment_id,
                    "client_id": client_id,
                    "service": service,
                    "scheduled_time": scheduled_time
                })
            )

            sns.publish(
                TopicArn=TEAM_NOTIFICATION_TOPIC_ARN,
                Subject="TeamNotification",
                Message=json.dumps({
                    "appointment_id": appointment_id,
                    "service": service,
                    "scheduled_time": scheduled_time,
                    "team_message": f"New appointment booked for {service}"
                })
            )

        except Exception:
            logger.exception("Failed to process appointment record")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}