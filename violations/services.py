"""Transaction-safe workflow operations for possible traffic incidents."""
from django.db import transaction

from accounts.models import User

from .models import AlertNotification, ViolationIncident


SIMULATION_DESCRIPTION = {
    ViolationIncident.ViolationType.OVERSPEEDING: "A simulated overspeeding indicator was produced.",
    ViolationIncident.ViolationType.RED_LIGHT: "A simulated red-light crossing indicator was produced.",
    ViolationIncident.ViolationType.RECKLESS: "A simulated reckless-driving indicator was produced.",
}


@transaction.atomic
def save_new_incident(*, form, user, simulated=False):
    incident = form.save(commit=False)
    incident.created_by = user
    incident.status = ViolationIncident.Status.PENDING
    incident.source = (
        ViolationIncident.Source.SIMULATED if simulated else ViolationIncident.Source.MANUAL
    )
    if simulated:
        generated = SIMULATION_DESCRIPTION[incident.violation_type]
        note = (incident.evidence_notes or "").strip()
        incident.evidence_notes = (
            "SIMULATED DETECTION - TEST DATA ONLY. No actual AI, camera, speed measurement "
            f"or traffic enforcement was performed. {generated}"
            + (f" Scenario note: {note}" if note else "")
        )
    incident.save()

    # In-app alerts, not email/SMS, to active administrators for review.
    administrators = User.objects.filter(role=User.Role.ADMIN, is_staff=True, is_active=True)
    alerts = [
        AlertNotification(
            recipient=administrator,
            incident=incident,
            kind=AlertNotification.Kind.NEW_INCIDENT,
            title=f"New pending violation #{incident.pk}",
            content=f"A {incident.get_violation_type_display().lower()} incident awaits review.",
        )
        for administrator in administrators
    ]
    if alerts:
        AlertNotification.objects.bulk_create(alerts, ignore_conflicts=True)
    return incident


class ReviewConflict(Exception):
    """Another review already completed; do not overwrite historical decisions."""


@transaction.atomic
def decide_incident(*, incident_id, reviewer, decision, notes):
    """Persist administrator decision, verified row, and creator alert atomically."""
    from django.core.exceptions import PermissionDenied
    from django.utils import timezone
    from .models import VerifiedViolation

    if not reviewer.is_roadguard_admin:
        raise PermissionDenied("Only RoadGuard administrators can verify incidents.")
    if decision not in (ViolationIncident.Status.APPROVED, ViolationIncident.Status.REJECTED):
        raise ValueError("Unsupported review decision")
    notes = (notes or "").strip()
    if len(notes) < 12:
        raise ValueError("A reason with at least 12 characters is required")

    incident = ViolationIncident.objects.select_for_update().get(pk=incident_id)
    if not incident.is_pending:
        raise ReviewConflict("This incident has already been reviewed. The original decision was retained.")

    now = timezone.now()
    incident.status = decision
    incident.reviewed_by = reviewer
    incident.reviewed_at = now
    incident.review_notes = notes
    incident.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])

    if decision == ViolationIncident.Status.APPROVED:
        VerifiedViolation.objects.create(incident=incident, verified_by=reviewer, verified_at=now)
        kind = AlertNotification.Kind.APPROVED
        title = f"Incident #{incident.pk} approved after review"
        body = "An authorized administrator verified your recorded incident in the prototype. No legal citation was issued."
    else:
        kind = AlertNotification.Kind.REJECTED
        title = f"Incident #{incident.pk} rejected after review"
        body = "An authorized administrator rejected your suspected incident. See the saved review notes."

    AlertNotification.objects.get_or_create(
        recipient=incident.created_by,
        incident=incident,
        kind=kind,
        defaults={"title": title, "content": body},
    )
    return incident
