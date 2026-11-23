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
