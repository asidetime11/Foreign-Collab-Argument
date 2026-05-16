from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import User
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from apps.ai.clients import chat_stream, ensure_ai_configured
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
    @override_settings(DUBRIFY_API_KEY="")
    def test_missing_api_key_raises_clear_configuration_error(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DUBRIFY_API_KEY"):
            ensure_ai_configured()

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

    @patch("apps.ai.clients._client")
    def test_chat_stream_skips_empty_provider_chunks(self, client_factory):
        class Delta:
            content = None

        class Choice:
            delta = Delta()

        class EmptyChunk:
            choices = []

        class TextChunk:
            choices = [Choice()]

        Choice.delta.content = "你好"
        client_factory.return_value.chat.completions.create.return_value = [EmptyChunk(), TextChunk()]

        self.assertEqual(list(chat_stream([{"role": "user", "content": "你好"}], "model")), ["你好"])

    @patch("apps.ai.clients.time.sleep", return_value=None)
    @patch("apps.ai.clients._client")
    def test_chat_stream_retries_once_when_provider_is_busy(self, client_factory, sleep):
        class Delta:
            content = "你好"

        class Choice:
            delta = Delta()

        class TextChunk:
            choices = [Choice()]

        client_factory.return_value.chat.completions.create.side_effect = [
            Exception("Error code: 429 - {'error': {'code': 'api_limit'}}"),
            [TextChunk()],
        ]

        self.assertEqual(list(chat_stream([{"role": "user", "content": "你好"}], "model")), ["你好"])
        self.assertEqual(client_factory.return_value.chat.completions.create.call_count, 2)
        sleep.assert_called_once()

    def test_chat_error_stream_uses_friendly_message_without_raw_exception(self):
        user = User.objects.create_user("p002", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1, current_step="chat", ai_mode=mode)
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", side_effect=IndexError("list index out of range")):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("暂时没有收到稳定回复", payload)
        self.assertNotIn("list index out of range", payload)

    def test_chat_error_stream_describes_provider_rate_limit(self):
        user = User.objects.create_user("p_rate_limit", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1, current_step="chat", ai_mode=mode)
        self.client.force_login(user)

        error = Exception("Error code: 429 - {'error': {'message': '当前分组上游负载已饱和，请稍后再试', 'code': 'api_limit'}}")
        with patch("apps.ai.views.chat_stream", side_effect=error):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("AI 服务现在比较拥挤", payload)
        self.assertNotIn("api_limit", payload)

    def test_chat_prompt_skips_empty_failed_assistant_messages(self):
        user = User.objects.create_user("p_skip_failed", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1, current_step="chat", ai_mode=mode)
        ConversationMessage.objects.create(round=round_obj, role="assistant", content="", language="zh-hans", error_message="Error code: 429")
        self.client.force_login(user)
        captured_messages = []

        def fake_chat_stream(messages, model):
            captured_messages.extend(messages)
            return iter(["好的"])

        with patch("apps.ai.views.chat_stream", side_effect=fake_chat_stream):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            b"".join(response.streaming_content)

        self.assertNotIn({"role": "assistant", "content": ""}, captured_messages)

    def test_chat_stream_encodes_multiline_markdown_as_sse_data_lines(self):
        user = User.objects.create_user("p003", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1, current_step="chat", ai_mode=mode)
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", return_value=iter(["**重点**\n- 第一条"])):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("data: **重点**\ndata: - 第一条\n\n", payload)
