from django.utils import timezone


def check_weather_for_appointment(appointment):
    """
    Replace this later with a real weather API.

    Current rule:
    - if service is not outdoor -> safe
    - if outdoor and scheduled hour is 15:00 or later -> weather risk
    """
    if not appointment.service.is_outdoor:
        return {"safe": True, "reason": "indoor_service"}

    local_dt = timezone.localtime(appointment.scheduled_date)
    if local_dt.hour >= 15:
        return {"safe": False, "reason": "high_wind_risk"}

    return {"safe": True, "reason": "clear"}