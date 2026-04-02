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


def get_mock_weather_risk(location):
    """
    Mock weather logic.
    Replace later with real weather API integration.
    """
    risky_locations = {"manchester", "glasgow"}
    if location and location.strip().lower() in risky_locations:
        return {"safe": False, "reason": "heavy_rain"}
    return {"safe": True, "reason": "clear"}


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        body = json.loads(event.get("body", "{}"))

        is_outdoor = body.get("is_outdoor")
        location = body.get("location", "")

        if is_outdoor is None:
            return build_response(
                400,
                {"error": "is_outdoor is required"}
            )

        if not is_outdoor:
            return build_response(
                200,
                {
                    "safe": True,
                    "reason": "indoor_work_no_weather_check_needed"
                }
            )

        weather_result = get_mock_weather_risk(location)

        logger.info("Weather check result: %s", weather_result)

        if not weather_result["safe"]:
            return build_response(
                200,
                {
                    "safe": False,
                    "reason": weather_result["reason"],
                    "message": "Weather conditions are not suitable for outdoor work",
                }
            )

        return build_response(
            200,
            {
                "safe": True,
                "reason": "clear",
                "message": "Weather conditions are suitable for outdoor work",
            }
        )

    except json.JSONDecodeError:
        logger.exception("Invalid JSON body")
        return build_response(
            400,
            {"error": "Invalid JSON request body"}
        )

    except Exception as e:
        logger.exception("Unexpected error during weather check")
        return build_response(
            500,
            {"error": "Internal server error", "details": str(e)}
        )