"""Complete WBS 1.3: detection, review, vehicle records, and alerts."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import role_required

from .forms import IncidentForm, IncidentReviewForm, VehicleRecordForm
from .models import AlertNotification, VehicleRecord, VerifiedViolation, ViolationIncident
from .permissions import personnel_required, visible_incidents, visible_vehicles
from .services import ReviewConflict, decide_incident, save_new_incident


@personnel_required
def vehicle_list(request):
    query = request.GET.get("q", "").strip()[:100]
    vehicles = visible_vehicles(request.user).select_related("created_by").annotate(incident_count=Count("incidents"))
    linked = request.GET.get("linked", "").strip()
    if linked == "yes":
        vehicles = vehicles.filter(incident_count__gt=0)
    elif linked == "no":
        vehicles = vehicles.filter(incident_count=0)
    if query:
        vehicles = vehicles.filter(Q(plate_number__icontains=query) | Q(description__icontains=query))
    return render(request, "violations/vehicle_list.html", {"vehicles": vehicles, "query": query, "linked": linked})


@personnel_required
def vehicle_create(request):
    form = VehicleRecordForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.created_by = request.user
        vehicle.save()
        messages.success(request, "Vehicle record saved to the database.")
        return redirect("violations:vehicle_detail", pk=vehicle.pk)
    return render(request, "violations/vehicle_form.html", {"form": form, "page_title": "Add vehicle record"})


@personnel_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(visible_vehicles(request.user).select_related("created_by"), pk=pk)
    incidents = visible_incidents(request.user).filter(vehicle=vehicle).order_by("-created_at")
    return render(request, "violations/vehicle_detail.html", {"vehicle": vehicle, "incidents": incidents})


@personnel_required
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(visible_vehicles(request.user), pk=pk)
    if vehicle.created_by_id != request.user.pk:
        raise PermissionDenied("Only the vehicle creator can edit this record.")
    if vehicle.incidents.exclude(status=ViolationIncident.Status.PENDING).exists():
        messages.error(request, "Vehicle records linked to reviewed incidents cannot be edited.")
        return redirect("violations:vehicle_detail", pk=pk)
    form = VehicleRecordForm(request.POST or None, instance=vehicle, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vehicle record updated.")
        return redirect("violations:vehicle_detail", pk=pk)
    return render(request, "violations/vehicle_form.html", {"form": form, "page_title": "Edit vehicle record", "vehicle": vehicle})


@personnel_required
@transaction.atomic
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(visible_vehicles(request.user).select_for_update(), pk=pk)
    if vehicle.created_by_id != request.user.pk:
        raise PermissionDenied("Only the vehicle creator can delete this record.")
    if request.method == "POST":
        if vehicle.incidents.exists():
            messages.error(request, "This vehicle is linked to incidents. Delete its pending incidents first; reviewed incidents are retained.")
            return redirect("violations:vehicle_detail", pk=pk)
        vehicle.delete()
        messages.success(request, "Unlinked vehicle record deleted.")
        return redirect("violations:vehicle_list")
    return render(request, "violations/vehicle_confirm_delete.html", {"vehicle": vehicle})


@personnel_required
def incident_list(request):
    incidents = visible_incidents(request.user).select_related("vehicle", "created_by", "reviewed_by")
    query = request.GET.get("q", "").strip()[:100]
    status = request.GET.get("status", "").strip()
    violation_type = request.GET.get("type", "").strip()
    if query:
        incidents = incidents.filter(Q(vehicle__plate_number__icontains=query) | Q(road_location__icontains=query))
    if status in ViolationIncident.Status.values:
        incidents = incidents.filter(status=status)
    if violation_type in ViolationIncident.ViolationType.values:
        incidents = incidents.filter(violation_type=violation_type)
    return render(request, "violations/incident_list.html", {
        "incidents": incidents,
        "query": query, "selected_status": status, "selected_type": violation_type,
        "statuses": ViolationIncident.Status.choices,
        "violation_types": ViolationIncident.ViolationType.choices,
    })


def _incident_create(request, *, simulated):
    initial = {"occurred_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")}
    form = IncidentForm(request.POST or None, user=request.user, simulated=simulated, initial=initial)
    if request.method == "POST" and form.is_valid():
        incident = save_new_incident(form=form, user=request.user, simulated=simulated)
        messages.success(request, "Simulated detection saved as pending review." if simulated else "Incident saved as pending review.")
        return redirect("violations:incident_detail", pk=incident.pk)
    return render(request, "violations/incident_form.html", {
        "form": form, "simulated": simulated,
        "page_title": "Run simulated detection" if simulated else "Record suspected violation",
        "has_vehicles": VehicleRecord.objects.filter(created_by=request.user).exists(),
    })


@personnel_required
def incident_create(request):
    return _incident_create(request, simulated=False)


@personnel_required
def incident_simulate(request):
    return _incident_create(request, simulated=True)


@personnel_required
def incident_detail(request, pk):
    incident = get_object_or_404(
        visible_incidents(request.user).select_related("vehicle", "created_by", "reviewed_by"), pk=pk
    )
    return render(request, "violations/incident_detail.html", {"incident": incident})


@personnel_required
@transaction.atomic
def incident_edit(request, pk):
    incident = get_object_or_404(visible_incidents(request.user).select_for_update(), pk=pk)
    if incident.created_by_id != request.user.pk:
        raise PermissionDenied("Only the creator can change this incident.")
    if not incident.is_pending:
        raise PermissionDenied("Reviewed incidents are locked to preserve the decision record.")
    form = IncidentForm(request.POST or None, instance=incident, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()  # The form never exposes status, source, creator, or review fields.
        messages.success(request, "Pending incident updated.")
        return redirect("violations:incident_detail", pk=pk)
    return render(request, "violations/incident_form.html", {
        "form": form, "simulated": False, "page_title": "Edit pending incident",
        "editing": True, "incident": incident, "has_vehicles": True,
    })


@personnel_required
@transaction.atomic
def incident_delete(request, pk):
    incident = get_object_or_404(visible_incidents(request.user).select_for_update(), pk=pk)
    if incident.created_by_id != request.user.pk:
        raise PermissionDenied("Only the creator can delete a pending incident.")
    if not incident.is_pending:
        raise PermissionDenied("Reviewed incidents cannot be deleted.")
    if request.method == "POST":
        incident.delete()  # New-incident notifications referencing this record cascade.
        messages.success(request, "Pending incident deleted.")
        return redirect("violations:incident_list")
    return render(request, "violations/incident_confirm_delete.html", {"incident": incident})


@role_required(User.Role.ADMIN)
def review_queue(request):
    query = request.GET.get("q", "").strip()[:100]
    violation_type = request.GET.get("type", "").strip()
    pending = ViolationIncident.objects.filter(status=ViolationIncident.Status.PENDING).select_related(
        "vehicle", "created_by"
    )
    if query:
        pending = pending.filter(Q(vehicle__plate_number__icontains=query) | Q(road_location__icontains=query))
    if violation_type in ViolationIncident.ViolationType.values:
        pending = pending.filter(violation_type=violation_type)
    return render(request, "violations/review_queue.html", {
        "pending": pending,
        "query": query,
        "selected_type": violation_type,
        "violation_types": ViolationIncident.ViolationType.choices,
    })


@role_required(User.Role.ADMIN)
def review_incident(request, pk):
    incident = get_object_or_404(
        ViolationIncident.objects.select_related("vehicle", "created_by", "reviewed_by"), pk=pk
    )
    if not incident.is_pending:
        messages.error(request, "This incident has already been reviewed and cannot be reviewed again.")
        return redirect("violations:incident_detail", pk=pk)
    form = IncidentReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reviewed = decide_incident(
                incident_id=pk,
                reviewer=request.user,
                decision=form.cleaned_data["decision"],
                notes=form.cleaned_data["review_notes"],
            )
        except ReviewConflict as exc:
            messages.error(request, str(exc))
            return redirect("violations:incident_detail", pk=pk)
        messages.success(
            request,
            "Incident approved; a verified record and creator alert were saved." if reviewed.status == ViolationIncident.Status.APPROVED
            else "Incident rejected; decision and creator alert were saved.",
        )
        return redirect("violations:incident_detail", pk=pk)
    return render(request, "violations/review_incident.html", {"form": form, "incident": incident})


@personnel_required
def verified_list(request):
    verified = VerifiedViolation.objects.select_related(
        "incident", "incident__vehicle", "incident__created_by", "verified_by"
    )
    if not request.user.is_roadguard_admin:
        verified = verified.filter(incident__created_by=request.user)
    return render(request, "violations/verified_list.html", {"verified": verified})


@personnel_required
def alert_list(request):
    unread_only = request.GET.get("unread") == "1"
    alerts = AlertNotification.objects.filter(recipient=request.user).select_related("incident")
    if unread_only:
        alerts = alerts.filter(read_at__isnull=True)
    return render(request, "violations/alert_list.html", {
        "alerts": alerts,
        "unread_only": unread_only,
        "unread_count": AlertNotification.objects.filter(recipient=request.user, read_at__isnull=True).count(),
    })


@personnel_required
@require_POST
def alert_mark_read(request, pk):
    alert = get_object_or_404(AlertNotification, pk=pk, recipient=request.user)
    alert.mark_read()
    messages.success(request, "Notification marked as read.")
    return redirect("violations:alert_list")


@personnel_required
@require_POST
def alert_delete(request, pk):
    alert = get_object_or_404(AlertNotification, pk=pk, recipient=request.user)
    alert.delete()
    messages.success(request, "Notification removed from your inbox.")
    return redirect("violations:alert_list")
