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
