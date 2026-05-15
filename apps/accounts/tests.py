from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ParticipantProfile
from apps.experiments.models import ExperimentBatch


class ParticipantProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="p001", password="pass")

        profile = ParticipantProfile.objects.get(user=user)

        self.assertEqual(profile.display_name, "")
        self.assertFalse(profile.has_required_display_name)

    def test_bulk_create_assigns_batch_and_passwords(self):
        admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        self.client.force_login(admin)

        response = self.client.post(
            reverse("admin:accounts_bulk_create"),
            {
                "batch": batch.pk,
                "initial_password": "initial-pass",
                "usernames": "p101\np102",
            },
        )

        self.assertEqual(response.status_code, 302)
        for username in ["p101", "p102"]:
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password("initial-pass"))
            self.assertEqual(user.participant_profile.batch, batch)

    def test_registration_page_is_linked_from_login(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, reverse("accounts:register"))

    def test_participant_can_register_and_get_default_batch(self):
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)

        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "new_participant",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )

        user = User.objects.get(username="new_participant")
        self.assertRedirects(response, reverse("accounts:profile_prompt"))
        self.assertEqual(user.participant_profile.batch, batch)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
