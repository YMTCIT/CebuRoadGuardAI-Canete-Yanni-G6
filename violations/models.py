"""Persistent violation-management records for the Cebu RoadGuard AI prototype.

Django ORM writes these tables to the existing Supabase PostgreSQL database.
No traffic camera/AI service or official citation mechanism is implied.
"""
import re

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


plate_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9 -]{1,18}[A-Z0-9]$",
    message="Enter 3-20 letters/numbers; spaces and hyphens are allowed between them.",
)


def normalize_plate(value):
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


class VehicleRecord(models.Model):
    plate_number = models.CharField(max_length=20, validators=[plate_validator])
    description = models.TextField(blank=True, max_length=500)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="roadguard_vehicles"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "plate_number"], name="unique_vehicle_plate_per_creator"
            ),
        ]

    def save(self, *args, **kwargs):
        self.plate_number = normalize_plate(self.plate_number)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.plate_number


class ViolationIncident(models.Model):
    class ViolationType(models.TextChoices):
        OVERSPEEDING = "OVERSPEEDING", "Overspeeding"
        RED_LIGHT = "RED_LIGHT", "Running a red light"
        RECKLESS = "RECKLESS", "Reckless driving"

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual sample incident"
        SIMULATED = "SIMULATED", "Simulated detection"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved / verified"
        REJECTED = "REJECTED", "Rejected"

    vehicle = models.ForeignKey(
        VehicleRecord, on_delete=models.PROTECT, related_name="incidents"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="roadguard_incidents"
    )
    violation_type = models.CharField(max_length=20, choices=ViolationType.choices)
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.MANUAL)
    road_location = models.CharField(max_length=160)
    occurred_at = models.DateTimeField()
    evidence_notes = models.TextField(blank=True, max_length=2000)
    evidence_url = models.URLField(blank=True, max_length=500)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="roadguard_reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="incident_status_created_idx"),
            models.Index(fields=["violation_type", "occurred_at"], name="incident_type_time_idx"),
        ]

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def __str__(self):
        return f"Incident #{self.pk or 'new'} ({self.get_violation_type_display()})"


class VerifiedViolation(models.Model):
    """A separate permanent record is saved only after administrator approval."""

    incident = models.OneToOneField(
        ViolationIncident, on_delete=models.PROTECT, related_name="verification"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="verified_violations"
    )
    verified_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-verified_at", "-pk"]

    def __str__(self):
        return f"Verified incident #{self.incident_id}"


class AlertNotification(models.Model):
    """In-app notifications addressed to one authenticated RoadGuard account."""

    class Kind(models.TextChoices):
        NEW_INCIDENT = "NEW_INCIDENT", "New incident to review"
        APPROVED = "APPROVED", "Incident approved"
        REJECTED = "REJECTED", "Incident rejected"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadguard_alerts"
    )
    incident = models.ForeignKey(
        ViolationIncident, on_delete=models.CASCADE, related_name="alerts"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=150)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "incident", "kind"],
                name="unique_alert_per_recipient_incident_kind"
            ),
        ]

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])

    def __str__(self):
        return self.title
