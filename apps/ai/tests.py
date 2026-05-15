from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.ai.prompts import build_system_prompt
from apps.experiments.models import AIMode, ExperimentBatch
from apps.survey.models import ConversationMessage, SurveySession, TopicRound


class PromptTests(TestCase):
    def test_prompt_contains_language_neutrality_and_mode_once(self):
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")

        prompt = build_system_prompt(batch, mode, "zh-hans")

        self.assertIn("适度中立", prompt)
        self.assertIn("中文", prompt)
        self.assertEqual(prompt.count("请总结信息。"), 1)

    def test_strict_neutrality_can_be_selected(self):
        batch = ExperimentBatch.objects.create(name="批次 A", ai_neutrality=ExperimentBatch.NEUTRALITY_STRICT)
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")

        prompt = build_system_prompt(batch, mode, "zh-hans")

        self.assertIn("严格中立", prompt)


class AIViewTests(TestCase):
    def test_chat_stream_saves_participant_and_assistant_messages(self):
        user = User.objects.create_user("p001", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1, current_step="chat", ai_mode=mode)
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", return_value=iter(["你", "好"])):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            list(response.streaming_content)

        self.assertEqual(ConversationMessage.objects.filter(round=round_obj, role="participant").count(), 1)
        self.assertEqual(ConversationMessage.objects.get(round=round_obj, role="assistant").content, "你好")
