import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ParticipantProfile
from apps.experiments.models import ExperimentBatch, ScaleItem, Topic
from apps.survey.models import QualityEvent, SurveySession
from apps.survey.services import current_step, get_or_create_session, submit_topic_order


class SurveyStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("p001", password="pass")
        self.batch = ExperimentBatch.objects.create(name="批次 A")
        self.user.participant_profile.display_name = "参与者"
        self.user.participant_profile.batch = self.batch
        self.user.participant_profile.save()
        for index in range(3):
            Topic.objects.create(
                batch=self.batch,
                title_zh=f"话题 {index}",
                title_en=f"Topic {index}",
                position=index,
            )

    def test_starting_session_snapshots_enabled_topics(self):
        session = get_or_create_session(self.user)

        self.assertEqual(len(session.topic_order_snapshot), 3)
        self.assertEqual(current_step(session), "topic_order")

    def test_topic_order_selects_high_low_and_locks_step(self):
        session = get_or_create_session(self.user)
        ids = [item["id"] for item in session.topic_order_snapshot]

        submit_topic_order(session, ids)
        session.refresh_from_db()

        self.assertEqual(session.selected_high_topic_id, ids[0])
        self.assertEqual(session.selected_low_topic_id, ids[-1])
        self.assertEqual(session.rounds.count(), 2)
        with self.assertRaises(PermissionError):
            submit_topic_order(session, ids)


class SurveyViewTests(TestCase):
    def test_anonymous_user_redirects_to_login(self):
        response = self.client.get(reverse("survey:start"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_missing_display_name_redirects_to_prompt(self):
        user = User.objects.create_user("p002", password="pass")
        self.client.force_login(user)

        response = self.client.get(reverse("survey:start"))

        self.assertRedirects(response, reverse("accounts:profile_prompt"))

    def test_missing_batch_shows_message(self):
        user = User.objects.create_user("p003", password="pass")
        user.participant_profile.display_name = "参与者"
        user.participant_profile.save()
        self.client.force_login(user)

        response = self.client.get(reverse("survey:start"))

        self.assertContains(response, "尚未分配实验批次")

    def test_quality_event_endpoint_records_event(self):
        user = User.objects.create_user("p004", password="pass")
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = ExperimentBatch.objects.create(name="批次 A")
        user.participant_profile.save()
        self.client.force_login(user)

        response = self.client.post(
            reverse("survey:quality_event"),
            data=json.dumps({"event_type": "copy", "metadata": {"key": "c"}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(QualityEvent.objects.filter(user=user, event_type="copy").count(), 1)
