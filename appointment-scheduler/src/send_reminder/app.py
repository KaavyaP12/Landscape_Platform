import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        body = event

        if "Records" in event:
            # SNS event
            sns_message = event["Records"][0]["Sns"]["Message"]
            body = json.loads(sns_message)

        required_fields = ["appointment_id", "client_id", "service", "scheduled_time"]
        missing_fields = [field for field in required_fields if field not in body]

        if missing_fields:
            return build_response(
                400,
                {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            )

        logger.info(
            "Sending reminder for appointment_id=%s client_id=%s service=%s scheduled_time=%s",
            body["appointment_id"],
            body["client_id"],
            body["service"],
            body["scheduled_time"],
        )

        # Replace later with SES, SMS provider, or email integration
        return build_response(
            200,
            {
                "message": "Reminder sent successfully",
                "appointment_id": body["appointment_id"],
            }
        )

    except Exception as e:
        logger.exception("Unexpected error while sending reminder")
        return build_response(
            500,
            {"error": "Internal server error", "details": str(e)}
        )