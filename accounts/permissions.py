"""Server-side role enforcement (not merely hiding navigation links)."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import User


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if role == User.Role.ADMIN and request.user.is_roadguard_admin:
                return view(request, *args, **kwargs)
            if role == User.Role.OFFICER and request.user.is_traffic_officer:
                return view(request, *args, **kwargs)
            raise PermissionDenied("This dashboard is restricted to the assigned role.")

        return wrapped

    return decorator
