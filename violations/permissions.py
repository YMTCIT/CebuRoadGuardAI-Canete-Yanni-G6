"""Role and ownership checks, always enforced in Django views."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def personnel_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_roadguard_admin or request.user.is_traffic_officer):
            raise PermissionDenied("A RoadGuard personnel role is required.")
        return view(request, *args, **kwargs)

    return wrapped


def visible_incidents(user):
    from .models import ViolationIncident

    queryset = ViolationIncident.objects.all()
    return queryset if user.is_roadguard_admin else queryset.filter(created_by=user)


def visible_vehicles(user):
    from .models import VehicleRecord

    queryset = VehicleRecord.objects.all()
    return queryset if user.is_roadguard_admin else queryset.filter(created_by=user)
