import asyncio
import time

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from openai import AsyncOpenAI, OpenAI


AI_CONFIGURATION_ERROR = "请先在后台的“模型和 API”页面配置 URL、API Key 和模型。"


def configured_providers():
    from apps.experiments.models import LLMProvider

    return list(
        LLMProvider.objects.filter(is_active=True, api_keys__is_active=True)
        .distinct()
        .order_by("priority", "id")
    )


def ensure_ai_configured():
    if not configured_providers():
        raise ImproperlyConfigured(AI_CONFIGURATION_ERROR)


def _default_provider():
    providers = configured_providers()
    if not providers:
        raise ImproperlyConfigured(AI_CONFIGURATION_ERROR)
    return providers[0]


def _client():
    client, _model_name = _get_client_for_provider(_default_provider())
    return client


def _get_client_for_provider(provider=None):
    if not provider:
        provider = _default_provider()

    if not provider.is_active:
        raise ValueError(f"LLM provider {provider.name} is disabled.")

    try:
        api_key_config = provider.get_next_api_key()
    except ValueError as exc:
        raise ImproperlyConfigured(f"无法获取 API Key: {exc}") from exc

    api_key_config.last_used_at = timezone.now()
    api_key_config.save(update_fields=["last_used_at"])

    model_name = api_key_config.default_model_name()
    if not model_name:
        raise ImproperlyConfigured("请在后台为 API Key 填写至少一个模型。")

    client = OpenAI(api_key=api_key_config.api_key, base_url=provider.base_url)
    provider._last_model_name = model_name
    return client, model_name


def _is_retryable_busy_error(exc):
    message = str(exc)
    return "429" in message or "api_limit" in message or "负载已饱和" in message


def chat_stream(messages, model=None, provider=None):
    attempts = 2
    client, model_name = _get_client_for_provider(provider or _default_provider())
    if model and not provider:
        model_name = model

    for attempt in range(attempts):
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
            )
            break
        except Exception as exc:
            if attempt == attempts - 1 or not _is_retryable_busy_error(exc):
                raise
            time.sleep(1)

    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = getattr(chunk.choices[0].delta, "content", "") or ""
        if delta:
            yield delta


def transcribe_audio(file_obj, model=None):
    client, _model_name = _get_client_for_provider(_default_provider())
    transcript = client.audio.transcriptions.create(
        model=model or settings.DEFAULT_TRANSCRIBE_MODEL,
        file=file_obj,
    )
    return getattr(transcript, "text", "")


async def _async_get_client_for_provider(provider):
    if not provider.is_active:
        raise ValueError(f"LLM provider {provider.name} is disabled.")

    try:
        api_key_config = await sync_to_async(provider.get_next_api_key)()
    except ValueError as exc:
        raise ImproperlyConfigured(f"无法获取 API Key: {exc}") from exc

    from apps.experiments.models import APIKey
    await APIKey.objects.filter(pk=api_key_config.pk).aupdate(last_used_at=timezone.now())

    model_name = api_key_config.default_model_name()
    if not model_name:
        raise ImproperlyConfigured("请在后台为 API Key 填写至少一个模型。")

    client = AsyncOpenAI(api_key=api_key_config.api_key, base_url=provider.base_url)
    provider._last_model_name = model_name
    return client, model_name


async def async_chat_stream(messages, provider):
    """async 流式生成器。调用方负责 fallback：连接失败前不 yield，raise 给调用方处理。"""
    attempts = 2
    client, model_name = await _async_get_client_for_provider(provider)

    stream = None
    for attempt in range(attempts):
        try:
            stream = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
            )
            break
        except Exception as exc:
            if attempt == attempts - 1 or not _is_retryable_busy_error(exc):
                raise
            await asyncio.sleep(1)

    async for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = getattr(chunk.choices[0].delta, "content", "") or ""
        if delta:
            yield delta
