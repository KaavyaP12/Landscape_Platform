import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

APPOINTMENTS_TABLE = os.environ["APPOINTMENTS_TABLE"]
APPOINTMENT_TOPIC_ARN = os.environ["APPOINTMENT_TOPIC_ARN"]

appointments_table = dynamodb.Table(APPOINTMENTS_TABLE)


def _json_decimal(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError


def lambda_handler(event, context):
    now = datetime.now(timezone.utc)
    upper_bound = now + timedelta(hours=24)

    logger.info("Scheduling reminders between %s and %s", now.isoformat(), upper_bound.isoformat())

    response = appointments_table.query(
        IndexName="ScheduleRangeIndex",
        KeyConditionExpression=Key("schedule_bucket").eq("APPOINTMENTS") &
                               Key("scheduled_datetime").between(now.isoformat(), upper_bound.isoformat())
    )

    published = 0
    for item in response.get("Items", []):
        if item.get("status") != "scheduled":
            continue

        sns.publish(
            TopicArn=APPOINTMENT_TOPIC_ARN,
            Subject="ReminderDue",
            Message=json.dumps(
                {
                    "event_type": "ReminderDue",
                    "appointment_id": item["appointment_id"],
                    "scheduled_datetime": item["scheduled_datetime"],
                },
                default=_json_decimal,
            ),
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": "ReminderDue"}
            },
        )
        published += 1

    logger.info("Published %s reminder events", published)
    return {"published": published}
