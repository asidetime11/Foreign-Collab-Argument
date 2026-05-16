import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI


def ensure_ai_configured():
    if not settings.DUBRIFY_API_KEY:
        raise ImproperlyConfigured("DUBRIFY_API_KEY is not configured. Please set it in .env before using AI chat or transcription.")


def _client():
    ensure_ai_configured()
    return OpenAI(api_key=settings.DUBRIFY_API_KEY, base_url=settings.DUBRIFY_BASE_URL)


def _is_retryable_busy_error(exc):
    message = str(exc)
    return "429" in message or "api_limit" in message or "负载已饱和" in message


def chat_stream(messages, model=None):
    attempts = 2
    for attempt in range(attempts):
        try:
            stream = _client().chat.completions.create(
                model=model or settings.DEFAULT_CHAT_MODEL,
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
