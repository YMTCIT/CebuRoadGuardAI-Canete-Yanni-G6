"""Account feature tests. Run with ROADGUARD_TEST_SQLITE=1 locally."""
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "StrongPass2026!A"


class AccountFeatureTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            "first_name": "Ana",
            "last_name": "Reyes",
            "username": "officer_ana",
            "email": "ana@example.com",
            "contact_number": "09171234567",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def create_officer(self, username="officer_existing", email="existing@example.com"):
        return User.objects.create_user(
            username=username, email=email, password=PASSWORD,
            role=User.Role.OFFICER, first_name="Cebu", last_name="Officer",
        )

    def create_admin(self):
        return User.objects.create_superuser(
            username="roadguard_admin", email="admin@example.com", password=PASSWORD
        )

    def test_registration_creates_an_officer_and_hashes_password(self):
        response = self.client.post(reverse("register"), self.registration_data())
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="officer_ana")
        self.assertEqual(user.role, User.Role.OFFICER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(check_password(PASSWORD, user.password))
        self.assertEqual(user.email, "ana@example.com")

    def test_public_registration_cannot_assign_itself_admin_role(self):
        data = self.registration_data(role="ADMIN", is_staff="on", is_superuser="on")
        self.client.post(reverse("register"), data)
        user = User.objects.get(username="officer_ana")
        self.assertEqual(user.role, User.Role.OFFICER)
        self.assertFalse(user.is_staff)

    def test_registration_validates_required_fields_and_email(self):
        response = self.client.post(reverse("register"), self.registration_data(email="not-an-email", first_name=""))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address")
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_duplicate_email_ignoring_case(self):
        self.create_officer(email="ana@example.com")
        response = self.client.post(reverse("register"), self.registration_data(email="ANA@EXAMPLE.COM"))
        self.assertContains(response, "An account with this email already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_registration_rejects_duplicate_username_ignoring_case(self):
        self.create_officer(username="Officer_Ana")
        response = self.client.post(reverse("register"), self.registration_data(username="officer_ana"))
        self.assertContains(response, "This username is already taken")
        self.assertEqual(User.objects.count(), 1)

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(reverse("register"), self.registration_data(password2="NotTheSame2026!"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password")
        self.assertEqual(User.objects.count(), 0)

    def test_successful_login_redirects_to_correct_officer_dashboard(self):
        self.create_officer()
        response = self.client.post(reverse("login"), {"username": "officer_existing", "password": PASSWORD})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        next_response = self.client.get(reverse("dashboard"))
        self.assertRedirects(next_response, reverse("officer_dashboard"))
        self.assertEqual(self.client.get(reverse("officer_dashboard")).status_code, 200)

    def test_invalid_credentials_produce_clear_message(self):
        self.create_officer()
        response = self.client.post(reverse("login"), {"username": "officer_existing", "password": "invalid"})
        self.assertContains(response, "Invalid username or password")

    def test_logout_ends_session_and_cannot_be_triggered_by_get(self):
        self.create_officer()
        self.client.login(username="officer_existing", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        response = self.client.get(reverse("officer_dashboard"))
        self.assertRedirects(response, reverse("login") + "?next=" + reverse("officer_dashboard"))

    def test_private_pages_redirect_anonymous_visitor_to_login(self):
        for url_name in ("dashboard", "admin_dashboard", "officer_dashboard", "profile"):
            with self.subTest(url=url_name):
                path = reverse(url_name)
                self.assertRedirects(self.client.get(path), reverse("login") + "?next=" + path)

    def test_officer_cannot_access_admin_dashboard_directly(self):
        self.create_officer()
        self.client.login(username="officer_existing", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 403)

    def test_admin_cannot_open_officer_dashboard_by_url(self):
        admin = self.create_admin()
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.client.login(username=admin.username, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("officer_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("admin_dashboard"))

    def test_login_ignores_untrusted_next_and_uses_role_dashboard(self):
        self.create_officer()
        url = reverse("login") + "?next=" + reverse("admin_dashboard")
        self.assertRedirects(
            self.client.post(url, {"username": "officer_existing", "password": PASSWORD}),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_profile_updates_only_current_user(self):
        first = self.create_officer()
        second = self.create_officer("officer_other", "other@example.com")
        self.client.login(username=first.username, password=PASSWORD)
        response = self.client.post(reverse("profile"), {
            "first_name": "Updated", "last_name": "Name", "email": "updated@example.com",
            "contact_number": "09990000000", "role": "ADMIN", "is_staff": "on",
        })
        self.assertRedirects(response, reverse("profile"))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.email, "updated@example.com")
        self.assertEqual(first.first_name, "Updated")
        self.assertEqual(first.role, User.Role.OFFICER)
        self.assertFalse(first.is_staff)
        self.assertEqual(second.email, "other@example.com")

    def test_profile_rejects_existing_email(self):
        first = self.create_officer()
        self.create_officer("officer_other", "other@example.com")
        self.client.login(username=first.username, password=PASSWORD)
        response = self.client.post(reverse("profile"), {
            "first_name": "Cebu", "last_name": "Officer", "email": "OTHER@EXAMPLE.COM",
            "contact_number": "09171234567",
        })
        self.assertContains(response, "An account with this email already exists")
        first.refresh_from_db()
        self.assertEqual(first.email, "existing@example.com")
