"""Django's protected administrative interface for account administration."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class RoadGuardUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Cebu RoadGuard details", {"fields": ("contact_number", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Cebu RoadGuard details", {"fields": ("email", "contact_number", "role")}),
    )
