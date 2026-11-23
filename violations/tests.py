"""Integration-like HTTP tests; SQLite permitted only with ROADGUARD_TEST_SQLITE=1."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AlertNotification, VehicleRecord, VerifiedViolation, ViolationIncident

User = get_user_model()
PASSWORD = "RoadGuardTest2026#"


class RoadGuardFixture:
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



class VehicleAndDetectionTests(RoadGuardFixture, TestCase):
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


class ReviewAndAlertTests(RoadGuardFixture, TestCase):
    """Exercise review integrity, dashboard role guards, and private notifications."""

    def create_pending(self, *, officer=None, vehicle=None):
        officer = officer or self.officer
        vehicle = vehicle or self.vehicle_a
        self.client.force_login(officer)
        response = self.client.post(
            reverse("violations:incident_create"),
            self.incident_data(vehicle=vehicle.pk),
        )
        self.assertEqual(response.status_code, 302)
        return ViolationIncident.objects.filter(created_by=officer).latest("pk")

    def review_data(self, decision="APPROVED", notes="The sample evidence is sufficient for prototype verification."):
        return {"decision": decision, "review_notes": notes}

    def test_review_queue_admin_only_and_unauthenticated_redirected(self):
        url = reverse("violations:review_queue")
        self.assertRedirects(self.client.get(url), reverse("login") + "?next=" + url)
        self.client.force_login(self.officer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_review_queue_violation_type_filter_keeps_only_matching_pending_records(self):
        overspeeding = self.create_pending()
        self.client.force_login(self.officer)
        red_light_response = self.client.post(
            reverse("violations:incident_create"),
            self.incident_data(violation_type=ViolationIncident.ViolationType.RED_LIGHT),
        )
        self.assertEqual(red_light_response.status_code, 302)
        red_light = ViolationIncident.objects.filter(
            created_by=self.officer, violation_type=ViolationIncident.ViolationType.RED_LIGHT
        ).latest("pk")

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("violations:review_queue"),
            {"type": ViolationIncident.ViolationType.RED_LIGHT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{red_light.pk}")
        self.assertNotContains(response, f"#{overspeeding.pk}")
        self.assertContains(response, 'value="RED_LIGHT" selected')

        combined = self.client.get(reverse("violations:review_queue"), {"q": "ABC", "type": "RED_LIGHT"})
        self.assertContains(combined, f"#{red_light.pk}")
        self.assertNotContains(combined, f"#{overspeeding.pk}")
        invalid = self.client.get(reverse("violations:review_queue"), {"type": "NOT_A_TYPE"})
        self.assertContains(invalid, f"#{red_light.pk}")
        self.assertContains(invalid, f"#{overspeeding.pk}")

    def test_admin_approval_saves_verified_record_and_owner_alert(self):
        incident = self.create_pending()
        self.client.force_login(self.officer)
        self.assertEqual(
            self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data()).status_code,
            403,
        )
        self.client.force_login(self.admin)
        result = self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data())
        self.assertRedirects(result, reverse("violations:incident_detail", args=[incident.pk]))
        incident.refresh_from_db()
        self.assertEqual(incident.status, "APPROVED")
        self.assertEqual(incident.reviewed_by, self.admin)
        self.assertIsNotNone(incident.reviewed_at)
        self.assertTrue(ViolationIncident.objects.filter(pk=incident.pk, reviewed_at__isnull=False).exists())
        self.assertEqual(VerifiedViolation.objects.filter(incident=incident, verified_by=self.admin).count(), 1)
        self.assertEqual(AlertNotification.objects.filter(recipient=self.officer, incident=incident, kind="APPROVED").count(), 1)
        self.client.force_login(self.officer)
        self.assertContains(self.client.get(reverse("violations:verified_list")), f"#{incident.pk}")
        self.assertContains(self.client.get(reverse("violations:alert_list")), "approved")

    def test_rejection_saves_reason_and_alert_but_no_verified_row(self):
        incident = self.create_pending()
        self.client.force_login(self.admin)
        self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data(
            decision="REJECTED", notes="Evidence does not justify approval in the sample dataset."
        ))
        incident.refresh_from_db()
        self.assertEqual(incident.status, "REJECTED")
        self.assertIn("does not justify", incident.review_notes)
        self.assertFalse(VerifiedViolation.objects.filter(incident=incident).exists())
        self.assertTrue(AlertNotification.objects.filter(recipient=self.officer, incident=incident, kind="REJECTED").exists())

    def test_review_requires_valid_choice_reason_and_cannot_be_repeated(self):
        incident = self.create_pending()
        self.client.force_login(self.admin)
        bad = self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data(notes="x"))
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(incident.status, "PENDING")
        invalid = self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data(decision="PENDING"))
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(VerifiedViolation.objects.count(), 0)
        self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data())
        repeated = self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data(decision="REJECTED"))
        self.assertEqual(repeated.status_code, 302)
        incident.refresh_from_db()
        self.assertEqual(incident.status, "APPROVED")
        self.assertEqual(VerifiedViolation.objects.filter(incident=incident).count(), 1)
        self.assertEqual(AlertNotification.objects.filter(recipient=self.officer, incident=incident, kind="APPROVED").count(), 1)

    def test_reviewed_incidents_and_vehicle_locked_against_edit_or_delete(self):
        incident = self.create_pending()
        self.client.force_login(self.admin)
        self.client.post(reverse("violations:review_incident", args=[incident.pk]), self.review_data())
        self.client.force_login(self.officer)
        for name in ("incident_edit", "incident_delete"):
            self.assertEqual(self.client.get(reverse(f"violations:{name}", args=[incident.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("violations:vehicle_edit", args=[self.vehicle_a.pk])).status_code, 302)
        self.assertEqual(self.client.post(reverse("violations:vehicle_delete", args=[self.vehicle_a.pk])).status_code, 302)
        self.assertTrue(VehicleRecord.objects.filter(pk=self.vehicle_a.pk).exists())

    def test_vehicle_and_incident_search_and_role_visibility(self):
        own = self.create_pending()
        others = self.create_pending(officer=self.other, vehicle=self.vehicle_b)
        self.client.force_login(self.officer)
        own_list = self.client.get(reverse("violations:incident_list"), {"status": "PENDING", "type": "OVERSPEEDING"})
        self.assertContains(own_list, f"#{own.pk}")
        self.assertNotContains(own_list, f"#{others.pk}")
        self.assertEqual(self.client.get(reverse("violations:incident_detail", args=[others.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("violations:review_queue")), "XYZ 5678")

    def test_private_alerts_mark_read_and_delete_only_with_post(self):
        incident = self.create_pending()
        alert = AlertNotification.objects.get(recipient=self.admin, incident=incident, kind="NEW_INCIDENT")
        self.client.force_login(self.officer)
        self.assertEqual(self.client.post(reverse("violations:alert_mark_read", args=[alert.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("violations:alert_delete", args=[alert.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("violations:alert_mark_read", args=[alert.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("violations:alert_delete", args=[alert.pk])).status_code, 405)
        self.assertRedirects(self.client.post(reverse("violations:alert_mark_read", args=[alert.pk])), reverse("violations:alert_list"))
        alert.refresh_from_db()
        self.assertIsNotNone(alert.read_at)
        self.assertEqual(self.client.get(reverse("violations:alert_list"), {"unread": 1}).status_code, 200)
        self.assertRedirects(self.client.post(reverse("violations:alert_delete", args=[alert.pk])), reverse("violations:alert_list"))
        self.assertFalse(AlertNotification.objects.filter(pk=alert.pk).exists())
        self.assertTrue(ViolationIncident.objects.filter(pk=incident.pk).exists())

    def test_role_dashboards_contain_working_links(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin_dashboard")), reverse("violations:review_queue"))
        self.client.force_login(self.officer)
        self.assertContains(self.client.get(reverse("officer_dashboard")), reverse("violations:incident_simulate"))
        self.assertEqual(self.client.get(reverse("violations:review_queue")).status_code, 403)


    def test_review_endpoint_requires_csrf(self):
        from django.test import Client
        incident = self.create_pending()
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.force_login(self.admin)
        response = strict_client.post(
            reverse("violations:review_incident", args=[incident.pk]), self.review_data()
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(VerifiedViolation.objects.filter(incident=incident).exists())

    def test_notifications_are_only_created_for_active_admins(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        incident = self.create_pending()
        self.assertFalse(AlertNotification.objects.filter(incident=incident, kind="NEW_INCIDENT").exists())
        self.assertTrue(ViolationIncident.objects.filter(pk=incident.pk).exists())

    def test_vehicle_has_incidents_filter(self):
        self.create_pending()
        self.client.force_login(self.officer)
        spare = VehicleRecord.objects.create(plate_number="SPARE 123", created_by=self.officer)
        has = self.client.get(reverse("violations:vehicle_list"), {"linked": "yes"})
        self.assertContains(has, "ABC 1234")
        self.assertNotContains(has, "SPARE 123")
        none = self.client.get(reverse("violations:vehicle_list"), {"linked": "no"})
        self.assertContains(none, "SPARE 123")
        self.assertNotContains(none, "ABC 1234")

    def test_posted_privilege_fields_cannot_change_incident_owner_or_status(self):
        incident = self.create_pending()
        self.client.force_login(self.officer)
        tampered = self.incident_data(
            created_by=self.other.pk,
            status="APPROVED",
            reviewed_by=self.admin.pk,
            source="LIVE_AI",
        )
        response = self.client.post(reverse("violations:incident_edit", args=[incident.pk]), tampered)
        self.assertEqual(response.status_code, 302)
        incident.refresh_from_db()
        self.assertEqual(incident.created_by, self.officer)
        self.assertEqual(incident.status, ViolationIncident.Status.PENDING)
        self.assertEqual(incident.source, ViolationIncident.Source.MANUAL)
        self.assertIsNone(incident.reviewed_by_id)

    def test_only_creator_can_delete_pending_record_even_for_admin(self):
        incident = self.create_pending()
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(reverse("violations:incident_delete", args=[incident.pk])).status_code, 403
        )
        self.assertTrue(ViolationIncident.objects.filter(pk=incident.pk).exists())
