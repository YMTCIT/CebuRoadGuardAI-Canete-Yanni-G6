"""Read-only oversight: never bypass the audited review workflow from Django admin."""
from django.contrib import admin

from .models import AlertNotification, VehicleRecord, VerifiedViolation, ViolationIncident


class AuditReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VehicleRecord)
class VehicleRecordAdmin(AuditReadOnlyAdmin):
    list_display = ("plate_number", "created_by", "created_at")
    search_fields = ("plate_number", "created_by__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ViolationIncident)
class ViolationIncidentAdmin(AuditReadOnlyAdmin):
    list_display = ("id", "vehicle", "violation_type", "status", "created_by", "created_at")
    list_filter = ("status", "violation_type", "source")
    search_fields = ("vehicle__plate_number", "road_location", "created_by__username")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")


@admin.register(VerifiedViolation)
class VerifiedViolationAdmin(AuditReadOnlyAdmin):
    list_display = ("incident", "verified_by", "verified_at")
    readonly_fields = ("incident", "verified_by", "verified_at")


@admin.register(AlertNotification)
class AlertNotificationAdmin(AuditReadOnlyAdmin):
    list_display = ("recipient", "kind", "incident", "created_at", "read_at")
    list_filter = ("kind",)
    readonly_fields = ("recipient", "incident", "kind", "title", "content", "created_at", "read_at")
