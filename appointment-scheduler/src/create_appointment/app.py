import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

APPOINTMENTS_TABLE = os.environ["APPOINTMENTS_TABLE"]
REMINDER_TOPIC_ARN = os.environ["REMINDER_TOPIC_ARN"]

appointments_table = dynamodb.Table(APPOINTMENTS_TABLE)


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def parse_iso_datetime(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        body = json.loads(event.get("body", "{}"))

        required_fields = ["client_id", "service", "scheduled_time", "is_outdoor"]
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return build_response(
                400,
                {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            )

        scheduled_time = parse_iso_datetime(body["scheduled_time"])
        if not scheduled_time:
            return build_response(
                400,
                {"error": "scheduled_time must be a valid ISO 8601 datetime"}
            )

        if scheduled_time <= datetime.now(timezone.utc):
            return build_response(
                400,
                {"error": "Appointment must be scheduled in the future"}
            )

        appointment_id = str(uuid.uuid4())

        item = {
            "appointment_id": appointment_id,
            "client_id": str(body["client_id"]),
            "service": body["service"],
            "scheduled_time": body["scheduled_time"],
            "is_outdoor": bool(body["is_outdoor"]),
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        appointments_table.put_item(Item=item)

        sns.publish(
            TopicArn=REMINDER_TOPIC_ARN,
            Subject="AppointmentCreated",
            Message=json.dumps({
                "appointment_id": appointment_id,
                "client_id": str(body["client_id"]),
                "service": body["service"],
                "scheduled_time": body["scheduled_time"],
            })
        )

        logger.info("Appointment created successfully: %s", appointment_id)

        return build_response(
            201,
            {
                "message": "Appointment created successfully",
                "appointment_id": appointment_id,
                "status": "scheduled",
            }
        )

    except ClientError as e:
        logger.exception("AWS error while creating appointment")
        return build_response(
            500,
            {"error": "AWS service error", "details": str(e)}
        )

    except json.JSONDecodeError:
        logger.exception("Invalid JSON body")
        return build_response(
            400,
            {"error": "Invalid JSON request body"}
        )

    except Exception as e:
        logger.exception("Unexpected error while creating appointment")
        return build_response(
            500,
            {"error": "Internal server error", "details": str(e)}
        )