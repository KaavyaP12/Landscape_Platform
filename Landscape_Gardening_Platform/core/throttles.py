from rest_framework.throttling import UserRateThrottle

class AppointmentUserRateThrottle(UserRateThrottle):
    rate = '50/min'