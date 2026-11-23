"""Account feature: register, login/logout, role dashboards, and own profile."""
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import ProfileForm, RegistrationForm, RoadGuardAuthenticationForm
from .models import User
from .permissions import role_required
from violations.models import VehicleRecord, ViolationIncident


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created successfully. You can now log in.")
        return redirect("login")
    return render(request, "accounts/register.html", {"form": form})


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = RoadGuardAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Every new login lands on a role-specific dashboard, not a user-supplied URL.
        return str(reverse_lazy("dashboard"))


@require_POST
@login_required
def sign_out(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.is_roadguard_admin:
        return redirect("admin_dashboard")
    if request.user.is_traffic_officer:
        return redirect("officer_dashboard")
    raise PermissionDenied("Your account does not have an assigned dashboard role.")


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "officer_count": User.objects.filter(role=User.Role.OFFICER, is_staff=False).count(),
        "admin_count": User.objects.filter(role=User.Role.ADMIN, is_staff=True).count(),
        "pending_count": ViolationIncident.objects.filter(status=ViolationIncident.Status.PENDING).count(),
        "vehicle_count": VehicleRecord.objects.count(),
    }
    return render(request, "accounts/admin_dashboard.html", context)


@role_required(User.Role.OFFICER)
def officer_dashboard(request):
    context = {
        "my_vehicle_count": VehicleRecord.objects.filter(created_by=request.user).count(),
        "my_incident_count": ViolationIncident.objects.filter(created_by=request.user).count(),
        "my_pending_count": ViolationIncident.objects.filter(created_by=request.user, status=ViolationIncident.Status.PENDING).count(),
    }
    return render(request, "accounts/officer_dashboard.html", context)


@login_required
def profile(request):
    # No user_id input: the only editable record is request.user.
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile was updated successfully.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})
