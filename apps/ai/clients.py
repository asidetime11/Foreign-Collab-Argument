import time
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from openai import OpenAI


def ensure_ai_configured():
    if not settings.DUBRIFY_API_KEY:
        raise ImproperlyConfigured("DUBRIFY_API_KEY is not configured. Please set it in .env before using AI chat or transcription.")


def _client():
    ensure_ai_configured()
    return OpenAI(api_key=settings.DUBRIFY_API_KEY, base_url=settings.DUBRIFY_BASE_URL)


def _get_client_for_provider(provider):
    """根据LLMProvider配置创建OpenAI客户端，使用轮询分配的API key"""
    if not provider:
        # 如果没有指定provider，使用默认配置
        return _client(), settings.DEFAULT_CHAT_MODEL

    if not provider.is_active:
        raise ValueError(f"LLM提供商 {provider.name} 未启用")

    # 从key池中获取下一个可用的key（轮询分配）
    try:
        api_key = provider.get_next_api_key()
    except ValueError as e:
        raise ImproperlyConfigured(f"无法获取API Key: {e}")

    # 更新最后使用时间
    from apps.experiments.models import APIKey
    APIKey.objects.filter(provider=provider, api_key=api_key).update(last_used_at=timezone.now())

    # 创建客户端
    client = OpenAI(api_key=api_key, base_url=provider.base_url)
    return client, provider.model_name


def _is_retryable_busy_error(exc):
    message = str(exc)
    return "429" in message or "api_limit" in message or "负载已饱和" in message


def chat_stream(messages, model=None, provider=None):
    """
    流式聊天

    Args:
        messages: 消息列表
        model: 模型名称（可选，如果指定provider则使用provider的model_name）
        provider: LLMProvider实例（可选，优先使用此配置）
    """
    attempts = 2

    if provider:
        # 使用provider配置
        client, model_name = _get_client_for_provider(provider)
    else:
        # 使用默认配置
        client = _client()
        model_name = model or settings.DEFAULT_CHAT_MODEL

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
    transcript = _client().audio.transcriptions.create(
        model=model or settings.DEFAULT_TRANSCRIBE_MODEL,
        file=file_obj,
    )
    return getattr(transcript, "text", "")

