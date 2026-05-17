from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.survey.models import ConversationMessage, TopicRound

from .clients import AI_CONFIGURATION_ERROR, chat_stream, configured_providers, transcribe_audio
from .prompts import build_system_prompt


def _sse_message(data, event=None):
    lines = []
    if event:
        lines.append(f"event: {event}")
    for line in str(data).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


def _friendly_chat_error(exc):
    message = str(exc)
    if AI_CONFIGURATION_ERROR in message or isinstance(exc, ImproperlyConfigured):
        return "AI 服务还没有在后台配置好，请联系管理员检查“模型和 API”。"
    if "429" in message or "api_limit" in message or "负载已饱和" in message:
        return "AI 服务现在比较拥挤，请稍后再试一次。"
    if "401" in message or "未提供令牌" in message or "Unauthorized" in message:
        return "AI 服务密钥没有正确配置，请联系管理员检查后台设置。"
    if "model_not_found" in message or "不存在" in message:
        return "当前模型名称不可用，请联系管理员在后台检查模型配置。"
    return "暂时没有收到稳定回复，请稍后再试一次。"


def _chat_providers():
    return configured_providers()


def _provider_display_model(provider):
    key = provider.api_keys.filter(is_active=True).order_by("usage_count", "id").first()
    if key:
        return key.default_model_name()
    return provider.model_name


@login_required
@require_POST
def chat(request, round_id):
    round_obj = get_object_or_404(TopicRound, pk=round_id, session__user=request.user)
    if round_obj.current_step != "chat" or not round_obj.ai_mode:
        return HttpResponseBadRequest("round is not in chat step")
    text = request.POST.get("message", "").strip()
    if not text:
        return HttpResponseBadRequest("message is required")

    providers = _chat_providers()
    initial_model_name = _provider_display_model(providers[0]) if providers else ""

    ConversationMessage.objects.create(
        round=round_obj,
        role="participant",
        content=text,
        language=round_obj.session.language,
        ai_mode_name=round_obj.ai_mode.name_zh,
        model_name=initial_model_name,
    )
    prior_messages = [
        {"role": "system", "content": build_system_prompt(round_obj.session.batch, round_obj.ai_mode, round_obj.session.language)}
    ]
    for message in round_obj.conversation_messages.order_by("created_at"):
        role = "assistant" if message.role == "assistant" else "user"
        if message.role in {"assistant", "participant"} and message.content.strip():
            prior_messages.append({"role": role, "content": message.content})

    def event_stream():
        errors = []
        if not providers:
            errors.append(ImproperlyConfigured(AI_CONFIGURATION_ERROR))

        for provider in providers:
            model_name = _provider_display_model(provider)
            try:
                chunks = list(chat_stream(prior_messages, provider=provider))
            except Exception as exc:  # pragma: no cover - network failure path.
                errors.append(exc)
                continue

            model_name = getattr(provider, "_last_model_name", model_name)
            for chunk in chunks:
                yield _sse_message(chunk)
            final = "".join(chunks)
            ConversationMessage.objects.create(
                round=round_obj,
                role="assistant",
                content=final,
                language=round_obj.session.language,
                ai_mode_name=round_obj.ai_mode.name_zh,
                model_name=model_name,
            )
            yield _sse_message("ok", event="done")
            return

        exc = errors[-1] if errors else ImproperlyConfigured(AI_CONFIGURATION_ERROR)
        friendly_message = _friendly_chat_error(exc)
        ConversationMessage.objects.create(
            round=round_obj,
            role="assistant",
            content="",
            language=round_obj.session.language,
            ai_mode_name=round_obj.ai_mode.name_zh,
            model_name=initial_model_name,
            error_message=str(exc),
        )
        yield _sse_message(friendly_message, event="error")

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_POST
def transcribe(request):
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return HttpResponseBadRequest("audio file is required")
    try:
        text = transcribe_audio(audio_file, settings.DEFAULT_TRANSCRIBE_MODEL)
    except ImproperlyConfigured as exc:
        return JsonResponse({"error": _friendly_chat_error(exc)}, status=503)
    return JsonResponse({"text": text, "model": settings.DEFAULT_TRANSCRIBE_MODEL})
