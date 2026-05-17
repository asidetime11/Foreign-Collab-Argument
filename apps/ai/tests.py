from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.ai.clients import chat_stream, ensure_ai_configured, transcribe_audio
from apps.ai.prompts import build_system_prompt
from apps.experiments.models import AIMode, APIKey, ExperimentBatch, LLMProvider
from apps.survey.models import ConversationMessage, SurveySession, TopicRound


class PromptTests(TestCase):
    def test_prompt_contains_language_instruction_and_mode_once(self):
        batch = ExperimentBatch.objects.create(name="Batch A")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。", prompt_en="Summarize the information.")

        prompt = build_system_prompt(batch, mode, "en")

        self.assertIn("Reply in English.", prompt)
        self.assertEqual(prompt.count("Summarize the information."), 1)

    def test_strict_neutrality_can_be_selected(self):
        batch = ExperimentBatch.objects.create(name="Batch A", ai_neutrality=ExperimentBatch.NEUTRALITY_STRICT)
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。", prompt_en="Summarize the information.")

        prompt = build_system_prompt(batch, mode, "en")

        self.assertIn("Stay strictly neutral", prompt)


class AIViewTests(TestCase):
    def _round(self, username="participant", language="zh-hans"):
        user = User.objects.create_user(username, password="pass")
        batch = ExperimentBatch.objects.create(name=f"Batch {username}")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, language=language, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(
            session=session,
            round_type=TopicRound.HIGH,
            topic_id=1,
            current_step="chat",
            ai_mode=mode,
        )
        return user, round_obj

    def _provider(self, name="provider", model="model-a", priority=1, key="key-a", key_models=""):
        provider = LLMProvider.objects.create(
            name=name,
            model_name=model,
            base_url=f"https://{name}.example/v1",
            priority=priority,
        )
        APIKey.objects.create(provider=provider, api_key=key, model_name=key_models, is_active=True)
        return provider

    def test_missing_backend_provider_raises_clear_configuration_error(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "后台"):
            ensure_ai_configured()

    def test_chat_stream_saves_participant_and_assistant_messages(self):
        user, round_obj = self._round("p001")
        self._provider()
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", return_value=iter(["你", "好"])):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            list(response.streaming_content)

        self.assertEqual(ConversationMessage.objects.filter(round=round_obj, role="participant").count(), 1)
        self.assertEqual(ConversationMessage.objects.get(round=round_obj, role="assistant").content, "你好")

    @patch("apps.ai.clients.OpenAI")
    def test_chat_stream_skips_empty_provider_chunks(self, openai_cls):
        class Delta:
            content = None

        class Choice:
            delta = Delta()

        class EmptyChunk:
            choices = []

        class TextChunk:
            choices = [Choice()]

        provider = self._provider()
        Choice.delta.content = "你好"
        openai_cls.return_value.chat.completions.create.return_value = [EmptyChunk(), TextChunk()]

        self.assertEqual(list(chat_stream([{"role": "user", "content": "你好"}], provider=provider)), ["你好"])

    @patch("apps.ai.clients.time.sleep", return_value=None)
    @patch("apps.ai.clients.OpenAI")
    def test_chat_stream_retries_once_when_provider_is_busy(self, openai_cls, sleep):
        class Delta:
            content = "你好"

        class Choice:
            delta = Delta()

        class TextChunk:
            choices = [Choice()]

        provider = self._provider()
        openai_cls.return_value.chat.completions.create.side_effect = [
            Exception("Error code: 429 - {'error': {'code': 'api_limit'}}"),
            [TextChunk()],
        ]

        self.assertEqual(list(chat_stream([{"role": "user", "content": "你好"}], provider=provider)), ["你好"])
        self.assertEqual(openai_cls.return_value.chat.completions.create.call_count, 2)
        sleep.assert_called_once()

    @patch("apps.ai.clients.OpenAI")
    def test_chat_stream_uses_model_attached_to_selected_api_key(self, openai_cls):
        class Delta:
            content = "ok"

        class Choice:
            delta = Delta()

        class TextChunk:
            choices = [Choice()]

        provider = LLMProvider.objects.create(
            name="shared-url",
            model_name="fallback-model",
            base_url="https://api.example.com/v1",
            priority=1,
        )
        older_key = APIKey.objects.create(provider=provider, api_key="key-a", model_name="model-a", usage_count=5)
        selected_key = APIKey.objects.create(provider=provider, api_key="key-b", model_name="model-b\nmodel-c", usage_count=0)
        openai_cls.return_value.chat.completions.create.return_value = [TextChunk()]

        chunks = list(chat_stream([{"role": "user", "content": "hi"}], provider=provider))

        self.assertEqual(chunks, ["ok"])
        openai_cls.assert_called_once_with(api_key="key-b", base_url="https://api.example.com/v1")
        openai_cls.return_value.chat.completions.create.assert_called_once_with(
            model="model-b",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
        selected_key.refresh_from_db()
        older_key.refresh_from_db()
        self.assertEqual(selected_key.usage_count, 1)
        self.assertIsNotNone(selected_key.last_used_at)
        self.assertEqual(older_key.usage_count, 5)

    def test_chat_error_stream_uses_friendly_message_without_raw_exception(self):
        user, round_obj = self._round("p002")
        self._provider()
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", side_effect=IndexError("list index out of range")):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("暂时没有收到稳定回复", payload)
        self.assertNotIn("list index out of range", payload)

    def test_chat_error_stream_describes_provider_rate_limit(self):
        user, round_obj = self._round("p_rate_limit")
        self._provider()
        self.client.force_login(user)

        error = Exception("Error code: 429 - {'error': {'message': '当前分组上游负载已饱和，请稍后再试', 'code': 'api_limit'}}")
        with patch("apps.ai.views.chat_stream", side_effect=error):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("AI 服务现在比较拥挤", payload)
        self.assertNotIn("api_limit", payload)

    def test_chat_prompt_skips_empty_failed_assistant_messages(self):
        user, round_obj = self._round("p_skip_failed")
        self._provider()
        ConversationMessage.objects.create(round=round_obj, role="assistant", content="", language="zh-hans", error_message="Error code: 429")
        self.client.force_login(user)
        captured_messages = []

        def fake_chat_stream(messages, provider=None, **kwargs):
            captured_messages.extend(messages)
            return iter(["好的"])

        with patch("apps.ai.views.chat_stream", side_effect=fake_chat_stream):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            b"".join(response.streaming_content)

        self.assertNotIn({"role": "assistant", "content": ""}, captured_messages)

    def test_chat_stream_encodes_multiline_markdown_as_sse_data_lines(self):
        user, round_obj = self._round("p003")
        self._provider()
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", return_value=iter(["**重点**\n- 第一条"])):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("data: **重点**\ndata: - 第一条\n\n", payload)

    def test_chat_tries_enabled_providers_by_priority_until_one_succeeds(self):
        user, round_obj = self._round("p_provider_fallback")
        first = self._provider(name="first", model="first-model", priority=1, key="first-key")
        second = self._provider(name="second", model="second-model", priority=2, key="second-key")
        self.client.force_login(user)
        attempted = []

        def fake_chat_stream(messages, provider=None, **kwargs):
            attempted.append(provider.name)
            if provider == first:
                raise Exception("Error code: 429 - {'error': {'code': 'api_limit'}}")
            return iter(["稳定", "回复"])

        with patch("apps.ai.views.chat_stream", side_effect=fake_chat_stream):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertEqual(attempted, ["first", "second"])
        self.assertIn("data: 稳定", payload)
        assistant = ConversationMessage.objects.get(round=round_obj, role="assistant")
        self.assertEqual(assistant.content, "稳定回复")
        self.assertEqual(assistant.model_name, "second-model")

    def test_chat_reports_friendly_error_after_all_providers_fail(self):
        user, round_obj = self._round("p_provider_fail")
        self._provider(name="broken", model="broken-model", key="broken-key")
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream", side_effect=Exception("upstream exploded")):
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("暂时没有收到稳定回复", payload)
        assistant = ConversationMessage.objects.get(round=round_obj, role="assistant")
        self.assertEqual(assistant.content, "")
        self.assertIn("upstream exploded", assistant.error_message)

    def test_chat_reports_backend_configuration_error_without_env_fallback(self):
        user, round_obj = self._round("p_no_provider")
        self.client.force_login(user)

        with patch("apps.ai.views.chat_stream") as chat:
            response = self.client.post(reverse("ai:chat", args=[round_obj.pk]), {"message": "你好"})
            payload = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("AI 服务还没有在后台配置好", payload)
        chat.assert_not_called()

    @patch("apps.ai.clients.OpenAI")
    def test_transcribe_audio_uses_backend_provider_credentials(self, openai_cls):
        self._provider(name="voice", model="chat-model", key="voice-key")
        openai_cls.return_value.audio.transcriptions.create.return_value.text = "语音转写结果"
        audio_file = SimpleUploadedFile("voice.webm", b"audio-bytes", content_type="audio/webm")

        text = transcribe_audio(audio_file, "gpt-4o-mini-transcribe")

        self.assertEqual(text, "语音转写结果")
        openai_cls.assert_called_once_with(api_key="voice-key", base_url="https://voice.example/v1")
        openai_cls.return_value.audio.transcriptions.create.assert_called_once_with(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
        )

    def test_transcribe_endpoint_returns_text_and_model(self):
        user = User.objects.create_user("p_voice", password="pass")
        self.client.force_login(user)
        audio_file = SimpleUploadedFile("voice.webm", b"audio-bytes", content_type="audio/webm")

        with patch("apps.ai.views.transcribe_audio", return_value="这是转写文字") as transcribe:
            response = self.client.post(reverse("ai:transcribe"), {"audio": audio_file})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "这是转写文字")
        self.assertEqual(response.json()["model"], "gpt-4o-mini-transcribe")
        transcribe.assert_called_once()
