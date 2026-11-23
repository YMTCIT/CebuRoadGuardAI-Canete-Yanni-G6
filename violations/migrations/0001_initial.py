# Initial Violation Management tables for the RoadGuard PD2 increment.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="VehicleRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plate_number", models.CharField(max_length=20, validators=[django.core.validators.RegexValidator(message="Enter 3-20 letters/numbers; spaces and hyphens are allowed between them.", regex="^[A-Z0-9][A-Z0-9 -]{1,18}[A-Z0-9]$")])),
                ("description", models.TextField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="roadguard_vehicles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.CreateModel(
            name="ViolationIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("violation_type", models.CharField(choices=[("OVERSPEEDING", "Overspeeding"), ("RED_LIGHT", "Running a red light"), ("RECKLESS", "Reckless driving")], max_length=20)),
                ("source", models.CharField(choices=[("MANUAL", "Manual sample incident"), ("SIMULATED", "Simulated detection")], default="MANUAL", max_length=12)),
                ("road_location", models.CharField(max_length=160)),
                ("occurred_at", models.DateTimeField()),
                ("evidence_notes", models.TextField(blank=True, max_length=2000)),
                ("evidence_url", models.URLField(blank=True, max_length=500)),
                ("status", models.CharField(choices=[("PENDING", "Pending review"), ("APPROVED", "Approved / verified"), ("REJECTED", "Rejected")], db_index=True, default="PENDING", max_length=12)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True, max_length=2000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="roadguard_incidents", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="roadguard_reviews", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents", to="violations.vehiclerecord")),
            ],
            options={"ordering": ["-created_at", "-pk"], "indexes": [models.Index(fields=["status", "created_at"], name="incident_status_created_idx"), models.Index(fields=["violation_type", "occurred_at"], name="incident_type_time_idx")]},
        ),
        migrations.CreateModel(
            name="VerifiedViolation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("verified_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("incident", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="verification", to="violations.violationincident")),
                ("verified_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="verified_violations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-verified_at", "-pk"]},
        ),
        migrations.CreateModel(
            name="AlertNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("NEW_INCIDENT", "New incident to review"), ("APPROVED", "Incident approved"), ("REJECTED", "Incident rejected")], max_length=20)),
                ("title", models.CharField(max_length=150)),
                ("content", models.TextField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="violations.violationincident")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="roadguard_alerts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="vehiclerecord",
            constraint=models.UniqueConstraint(fields=("created_by", "plate_number"), name="unique_vehicle_plate_per_creator"),
        ),
        migrations.AddConstraint(
            model_name="alertnotification",
            constraint=models.UniqueConstraint(fields=("recipient", "incident", "kind"), name="unique_alert_per_recipient_incident_kind"),
        ),
    ]
