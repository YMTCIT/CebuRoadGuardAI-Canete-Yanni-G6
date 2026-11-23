"""Integration-like HTTP tests; SQLite permitted only with ROADGUARD_TEST_SQLITE=1."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AlertNotification, VehicleRecord, ViolationIncident

User = get_user_model()
PASSWORD = "RoadGuardTest2026#"


class VehicleAndDetectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.officer = User.objects.create_user(username="officer_a", email="a@example.com", password=PASSWORD)
        cls.other = User.objects.create_user(username="officer_b", email="b@example.com", password=PASSWORD)
        cls.admin = User.objects.create_superuser(username="admin_a", email="admin_a@example.com", password=PASSWORD)
        cls.vehicle_a = VehicleRecord.objects.create(plate_number="ABC 1234", description="Demo record", created_by=cls.officer)
        cls.vehicle_b = VehicleRecord.objects.create(plate_number="XYZ 5678", created_by=cls.other)

    def incident_data(self, vehicle=None, **updates):
        data = {
            "vehicle": vehicle or self.vehicle_a.pk,
            "violation_type": ViolationIncident.ViolationType.OVERSPEEDING,
            "road_location": "Cebu City sample road",
            "occurred_at": timezone.localtime(timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "evidence_notes": "Manual sample observation, no AI used.",
            "evidence_url": "",
        }
        data.update(updates)
        return data

    def test_anonymous_users_cannot_open_core_pages(self):
        for name in ("vehicle_list", "vehicle_create", "incident_list", "incident_create", "incident_simulate"):
            with self.subTest(view=name):
                url = reverse(f"violations:{name}")
                self.assertRedirects(self.client.get(url), reverse("login") + "?next=" + url)

    def test_officer_vehicle_create_normalizes_plate_and_owns_record(self):
        self.client.force_login(self.officer)
        response = self.client.post(reverse("violations:vehicle_create"), {"plate_number": "def- 5555", "description": "Test"})
        self.assertEqual(response.status_code, 302)
        vehicle = VehicleRecord.objects.get(plate_number="DEF- 5555")
        self.assertEqual(vehicle.created_by, self.officer)
        self.assertEqual(self.client.get(reverse("violations:vehicle_detail", args=[vehicle.pk])).status_code, 200)

    def test_duplicate_vehicle_and_bad_plate_rejected(self):
        self.client.force_login(self.officer)
        response = self.client.post(reverse("violations:vehicle_create"), {"plate_number": "abc 1234", "description": "Duplicate"})
        self.assertContains(response, "already have a vehicle")
        response = self.client.post(reverse("violations:vehicle_create"), {"plate_number": "@?", "description": "Bad"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(VehicleRecord.objects.filter(created_by=self.officer).count(), 1)

    def test_officer_cannot_view_or_modify_another_vehicle(self):
        self.client.force_login(self.officer)
        for name in ("vehicle_detail", "vehicle_edit", "vehicle_delete"):
            self.assertEqual(self.client.get(reverse(f"violations:{name}", args=[self.vehicle_b.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("violations:vehicle_list")), "XYZ 5678")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("violations:vehicle_list")), "XYZ 5678")
        self.assertEqual(self.client.get(reverse("violations:vehicle_edit", args=[self.vehicle_b.pk])).status_code, 403)

    def test_vehicle_update_and_delete_restricted_when_incidents_linked(self):
        self.client.force_login(self.officer)
        self.assertEqual(self.client.post(reverse("violations:vehicle_edit", args=[self.vehicle_a.pk]), {"plate_number": "NEW-1234", "description": "Changed"}).status_code, 302)
        self.vehicle_a.refresh_from_db()
        self.assertEqual(self.vehicle_a.plate_number, "NEW-1234")
        vehicle = VehicleRecord.objects.create(plate_number="FREE-1234", created_by=self.officer)
        self.assertEqual(self.client.post(reverse("violations:vehicle_delete", args=[vehicle.pk])).status_code, 302)
        self.assertFalse(VehicleRecord.objects.filter(pk=vehicle.pk).exists())
        self.client.post(reverse("violations:incident_create"), self.incident_data())
        response = self.client.post(reverse("violations:vehicle_delete", args=[self.vehicle_a.pk]))
        self.assertRedirects(response, reverse("violations:vehicle_detail", args=[self.vehicle_a.pk]))
        self.assertTrue(VehicleRecord.objects.filter(pk=self.vehicle_a.pk).exists())

    def test_manual_incident_create_saves_pending_record_and_alerts_admin(self):
        self.client.force_login(self.officer)
        response = self.client.post(reverse("violations:incident_create"), self.incident_data())
        self.assertEqual(response.status_code, 302)
        incident = ViolationIncident.objects.get(created_by=self.officer)
        self.assertEqual(incident.status, ViolationIncident.Status.PENDING)
        self.assertEqual(incident.source, ViolationIncident.Source.MANUAL)
        self.assertEqual(incident.vehicle, self.vehicle_a)
        self.assertEqual(AlertNotification.objects.filter(recipient=self.admin, incident=incident).count(), 1)
        self.assertContains(self.client.get(reverse("violations:incident_detail", args=[incident.pk])), "Manual sample observation")

    def test_simulated_detection_is_explicitly_labeled(self):
        self.client.force_login(self.officer)
        data = self.incident_data(evidence_notes="")
        response = self.client.post(reverse("violations:incident_simulate"), data)
        self.assertEqual(response.status_code, 302)
        incident = ViolationIncident.objects.get(created_by=self.officer)
        self.assertEqual(incident.source, ViolationIncident.Source.SIMULATED)
        self.assertIn("No actual AI", incident.evidence_notes)
        self.assertEqual(incident.status, ViolationIncident.Status.PENDING)

    def test_incident_validation_blocks_foreign_vehicles_future_time_and_missing_notes(self):
        self.client.force_login(self.officer)
        bad_vehicle = self.client.post(reverse("violations:incident_create"), self.incident_data(vehicle=self.vehicle_b.pk))
        self.assertContains(bad_vehicle, "Select a valid choice")
        future = (timezone.localtime(timezone.now()) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        bad_date = self.client.post(reverse("violations:incident_create"), self.incident_data(occurred_at=future))
        self.assertContains(bad_date, "cannot be in the future")
        bad_notes = self.client.post(reverse("violations:incident_create"), self.incident_data(evidence_notes="x"))
        self.assertContains(bad_notes, "at least 12 characters")
        self.assertEqual(ViolationIncident.objects.count(), 0)

    def test_creator_can_edit_and_delete_pending_incident_but_other_officer_cannot(self):
        self.client.force_login(self.officer)
        self.client.post(reverse("violations:incident_create"), self.incident_data())
        incident = ViolationIncident.objects.get(created_by=self.officer)
        self.client.force_login(self.other)
        for name in ("incident_detail", "incident_edit", "incident_delete"):
            self.assertEqual(self.client.get(reverse(f"violations:{name}", args=[incident.pk])).status_code, 404)
        self.client.force_login(self.officer)
        edited = self.incident_data(road_location="Updated Cebu road")
        self.assertEqual(self.client.post(reverse("violations:incident_edit", args=[incident.pk]), edited).status_code, 302)
        incident.refresh_from_db()
        self.assertEqual(incident.road_location, "Updated Cebu road")
        self.assertEqual(self.client.post(reverse("violations:incident_delete", args=[incident.pk])).status_code, 302)
        self.assertFalse(ViolationIncident.objects.filter(pk=incident.pk).exists())
        self.assertFalse(AlertNotification.objects.filter(incident_id=incident.pk).exists())

    def test_admin_views_all_incidents_officer_sees_own(self):
        self.client.force_login(self.other)
        self.client.post(reverse("violations:incident_create"), self.incident_data(vehicle=self.vehicle_b.pk))
        incident = ViolationIncident.objects.get(created_by=self.other)
        self.client.force_login(self.officer)
        self.assertNotContains(self.client.get(reverse("violations:incident_list")), f"#{incident.pk}")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("violations:incident_list")), f"#{incident.pk}")
        filtered = self.client.get(reverse("violations:incident_list"), {"q": "XYZ 5678"})
        self.assertContains(filtered, "XYZ 5678")
