"""Django-auth based user roles for the RoadGuard prototype."""
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower


class RoadGuardUserManager(DjangoUserManager):
    """Create Django users normally; reserve the admin role for superusers."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "OFFICER")
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = "ADMIN"
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        OFFICER = "OFFICER", "Traffic Officer"

    email = models.EmailField("email address", unique=True)
    contact_number = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.OFFICER)

    objects = RoadGuardUserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_insensitive_unique"),
            models.UniqueConstraint(Lower("username"), name="accounts_username_case_insensitive_unique"),
        ]

    def save(self, *args, **kwargs):
        self.username = self.username.strip()
        self.email = (self.email or "").strip().lower()
        return super().save(*args, **kwargs)

    @property
    def is_roadguard_admin(self):
        return self.role == self.Role.ADMIN and self.is_staff

    @property
    def is_traffic_officer(self):
        return self.role == self.Role.OFFICER and not self.is_staff
