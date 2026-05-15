from django.conf import settings
from openai import OpenAI


def _client():
    return OpenAI(api_key=settings.DUBRIFY_API_KEY, base_url=settings.DUBRIFY_BASE_URL)


def chat_stream(messages, model=None):
    stream = _client().chat.completions.create(
        model=model or settings.DEFAULT_CHAT_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


def transcribe_audio(file_obj, model=None):
    transcript = _client().audio.transcriptions.create(
        model=model or settings.DEFAULT_TRANSCRIBE_MODEL,
        file=file_obj,
    )
    return getattr(transcript, "text", "")
