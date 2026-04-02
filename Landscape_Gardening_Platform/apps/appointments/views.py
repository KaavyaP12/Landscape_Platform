from urllib import request

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from datetime import datetime, time
from rest_framework.response import Response
from rest_framework import status
from core.pagination import AppointmentPagination
from .serializer import AppointmentSerializer, AppointmentRequestSerializer
from core.throttles import AppointmentUserRateThrottle
from .models import Appointment
from rest_framework.decorators import api_view, throttle_classes
# from .services import request_appointment, publish_event
from .services import create_appointment_with_validation, publish_event

# VALID_STATUSES = {'scheduled', 'in_progress', 'completed', 'cancelled'}

VALID_STATUSES = {
    "requested",
    "scheduled",
    "weather_blocked",
    "team_unavailable",
    "in_progress",
    "completed",
    "cancelled",
}

# Create your views here.
@api_view(['GET'])
@throttle_classes([AppointmentUserRateThrottle])  # Disable throttling for this view
def appointment_list_api(request):
    try:
        queryset = Appointment.objects.select_related('client', 'service').all().order_by('scheduled_date')
        status_param = request.GET.get('status')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if status_param:
            if status_param not in VALID_STATUSES:
                return Response(
                    {"error": "Invalid status value.",
                        "allowed_values": list(VALID_STATUSES)},
                    status = status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(status=status_param)
        if start_date:
            parsed_start = parse_date(start_date)
            if not parsed_start:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            start_datetime = make_aware(datetime.combine(parsed_start, time.min))
            queryset = queryset.filter(scheduled_date__gte=start_datetime)

        if end_date:
            parsed_end = parse_date(end_date)
            if not parsed_end:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            end_datetime = make_aware(datetime.combine(parsed_end, time.max))
            queryset = queryset.filter(scheduled_date__lte=end_datetime)

        if start_date and end_date:
            if parsed_start > parsed_end:
                return Response(
                    {"error": "start_date cannot be later than end_date."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        paginator = AppointmentPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = AppointmentSerializer(paginated_queryset, many=True)
       
        return paginator.get_paginated_response(serializer.data)
        
    except Exception as e:
        return Response(
            {"error": "Something went wrong while fetching appointments.", 
             "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    # appointment_list = Appointment.objects.select_related('client', 'service').all()   
    # for appointment in appointment_list:
    #     print(f"Appointment {appointment.id} for {appointment.client.name}")
    #     print(f"  - Service: {appointment.service.name}")
    #     print(f"  - Scheduled: {appointment.scheduled_date}") 

    # return JsonResponse({'appointments': list(appointment_list.values())})


@api_view(["GET"])
@throttle_classes([AppointmentUserRateThrottle])
def appointment_list_api(request):
    try:
        queryset = Appointment.objects.select_related(
            "client",
            "service",
            "assigned_team_member__user",
        ).all().order_by("scheduled_date")

        status_param = request.GET.get("status")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if status_param:
            if status_param not in VALID_STATUSES:
                return Response(
                    {
                        "error": "Invalid status value.",
                        "allowed_values": sorted(list(VALID_STATUSES)),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(status=status_param)

        parsed_start = None
        parsed_end = None

        if start_date:
            parsed_start = parse_date(start_date)
            if not parsed_start:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(
                scheduled_date__gte=make_aware(datetime.combine(parsed_start, time.min))
            )

        if end_date:
            parsed_end = parse_date(end_date)
            if not parsed_end:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(
                scheduled_date__lte=make_aware(datetime.combine(parsed_end, time.max))
            )

        if parsed_start and parsed_end and parsed_start > parsed_end:
            return Response(
                {"error": "start_date cannot be later than end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        paginator = AppointmentPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AppointmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    except Exception as exc:
        return Response(
            {
                "error": "Something went wrong while fetching appointments.",
                "details": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@throttle_classes([AppointmentUserRateThrottle])
def appointment_request_api(request):
    serializer = AppointmentRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        appointment = create_appointment_with_validation(**serializer.validated_data)
        return Response(
            {
                "message": "Appointment request accepted.",
                "appointment_id": appointment.id,
                "status": appointment.status,
            },
            status=status.HTTP_201_CREATED,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response(
            {"error": "Failed to create appointment request.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def simulate_weather_change_api(request, appointment_id):
    publish_event(
        event_type="WeatherChanged",
        aggregate_type="Appointment",
        aggregate_id=appointment_id,
        payload={"appointment_id": appointment_id},
    )
    return Response({"message": "WeatherChanged event published."}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
def simulate_team_unavailable_api(request, team_member_id):
    publish_event(
        event_type="TeamMemberUnavailable",
        aggregate_type="TeamMember",
        aggregate_id=team_member_id,
        payload={"team_member_id": team_member_id},
    )
    return Response({"message": "TeamMemberUnavailable event published."}, status=status.HTTP_202_ACCEPTED)