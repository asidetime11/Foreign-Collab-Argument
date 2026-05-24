import asyncio
import hashlib
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


def chat_providers():
    from apps.experiments.models import LLMProvider

    return list(
        LLMProvider.objects.filter(
            is_active=True, api_keys__is_active=True, kind=LLMProvider.KIND_CHAT
        )
        .distinct()
        .order_by("priority", "id")
    )


def transcribe_providers():
    from apps.experiments.models import LLMProvider

    return list(
        LLMProvider.objects.filter(
            is_active=True, api_keys__is_active=True, kind=LLMProvider.KIND_TRANSCRIBE
        )
        .distinct()
        .order_by("priority", "id")
    )


def ensure_ai_configured():
    if not chat_providers():
        raise ImproperlyConfigured(AI_CONFIGURATION_ERROR)


def _default_provider():
    providers = chat_providers()
    if not providers:
        raise ImproperlyConfigured(AI_CONFIGURATION_ERROR)
    return providers[0]


def _client():
    client, _model_name = _get_client_for_provider(_default_provider())
    return client


def _preview_api_key(value):
    if not value:
        return ""
    if len(value) <= 12:
        return value
    return f"{value[:8]}...{value[-4:]}"


def _get_client_for_provider(provider=None, model_name=None):
    if not provider:
        provider = _default_provider()

    if not provider.is_active:
        raise ValueError(f"LLM provider {provider.name} is disabled.")

    try:
        api_key_config = provider.get_next_api_key(model_name=model_name)
    except ValueError as exc:
        raise ImproperlyConfigured(f"无法获取 API Key: {exc}") from exc

    api_key_config.last_used_at = timezone.now()
    api_key_config.save(update_fields=["last_used_at"])

    selected_model_name = model_name or api_key_config.default_model_name()
    if not selected_model_name:
        raise ImproperlyConfigured("请在后台为 API Key 填写至少一个模型。")

    client = OpenAI(api_key=api_key_config.api_key, base_url=provider.base_url)
    provider._last_model_name = selected_model_name
    provider._last_api_key_preview = _preview_api_key(api_key_config.api_key)
    return client, selected_model_name


def _get_client_for_model(model_name):
    providers = transcribe_providers()
    if not providers:
        raise ImproperlyConfigured(
            "请到后台「模型和 API」页面的「语音」分页配置语音转写供应商。"
        )

    errors = []
    for provider in providers:
        try:
            client, selected_model_name = _get_client_for_provider(provider, model_name=model_name)
            return client, selected_model_name, provider
        except ImproperlyConfigured as exc:
            errors.append(str(exc))

    detail = "；".join(errors)
    raise ImproperlyConfigured(
        f"转写模型 {model_name} 未在任何启用的语音供应商中配置。"
        f"请到后台「模型和 API」→「语音」分页，在对应 Key 的“支持模型”里添加 {model_name}。"
        f"{' ' + detail if detail else ''}"
    )


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
    model_name = model or settings.DEFAULT_TRANSCRIBE_MODEL
    client, model_name, provider = _get_client_for_model(model_name)
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    audio_bytes = file_obj.read()
    audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
    upload_file = (
        getattr(file_obj, "name", "recording.webm"),
        audio_bytes,
        getattr(file_obj, "content_type", "application/octet-stream"),
    )
    print(
        (
            "[transcribe] calling provider: "
            f"provider={provider.name} base_url={provider.base_url} "
            f"model={model_name} key={getattr(provider, '_last_api_key_preview', '')} "
            f"audio_name={upload_file[0]} audio_bytes={len(audio_bytes)} "
            f"audio_sha256_16={audio_hash} content_type={upload_file[2]}"
        ),
        flush=True,
    )
    transcript = client.audio.transcriptions.create(
        model=model_name,
        file=upload_file,
    )
    text = getattr(transcript, "text", "")
    print(f"[transcribe] provider returned text: {text!r}", flush=True)
    return text


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
    provider._last_api_key_preview = _preview_api_key(api_key_config.api_key)
    return client, model_name


async def async_chat_stream(messages, provider):
    attempts = 2
    t0 = time.monotonic()
    client, model_name = await _async_get_client_for_provider(provider)
    t1 = time.monotonic()
    print(f"[ttft] client built dt={t1-t0:.3f}s base_url={provider.base_url} model={model_name}", flush=True)

    stream = None
    for attempt in range(attempts):
        try:
            t2 = time.monotonic()
            stream = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
            )
            t3 = time.monotonic()
            print(f"[ttft] create() returned dt={t3-t2:.3f}s (attempt={attempt})", flush=True)
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
