import logging
import time

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.survey.models import ConversationMessage, TopicRound

from .clients import AI_CONFIGURATION_ERROR, async_chat_stream, configured_providers, transcribe_audio
from .prompts import build_system_prompt


logger = logging.getLogger(__name__)


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
        return 'AI 服务还没有在后台配置好，请联系管理员检查"模型和 API"。'
    if "429" in message or "api_limit" in message or "负载已饱和" in message:
        return "AI 服务现在比较拥挤，请稍后再试一次。"
    if "401" in message or "未提供令牌" in message or "Unauthorized" in message:
        return "AI 服务密钥没有正确配置，请联系管理员检查后台设置。"
    if "model_not_found" in message or "不存在" in message:
        return "当前模型名称不可用，请联系管理员在后台检查模型配置。"
    return "暂时没有收到稳定回复，请稍后再试一次。"


def _friendly_transcribe_error(exc):
    message = str(exc)
    if isinstance(exc, ImproperlyConfigured) or AI_CONFIGURATION_ERROR in message:
        return "语音转写配置还没有准备好。"
    if "model_price_error" in message or "ratio or price not set" in message or "倍率或价格未配置" in message:
        return (
            "语音转写失败：当前转写模型没有在 API 代理中配置价格/倍率。"
            "请把 DEFAULT_TRANSCRIBE_MODEL 改为代理支持的转写模型（例如 whisper-1），"
            "或在代理后台为该模型配置价格。"
        )
    if "model_not_found" in message or "不存在" in message:
        return "语音转写失败：当前转写模型名称不可用，请检查后台模型配置。"
    return "语音转写失败，请检查转写模型或 API 分组是否支持 audio/transcriptions。"


async def _async_chat_providers():
    return await sync_to_async(configured_providers)()


async def _async_provider_display_model(provider):
    key = await provider.api_keys.filter(is_active=True).order_by("usage_count", "id").afirst()
    if key:
        return key.default_model_name()
    return provider.model_name


async def chat(request, round_id):
    user = await request.auser()
    if not user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        round_obj = await TopicRound.objects.select_related(
            "session__batch", "session", "ai_mode"
        ).aget(pk=round_id, session__user=user)
    except TopicRound.DoesNotExist:
        raise Http404

    if round_obj.current_step != "chat" or not round_obj.ai_mode:
        return HttpResponseBadRequest("round is not in chat step")

    text = request.POST.get("message", "").strip()
    if not text:
        return HttpResponseBadRequest("message is required")

    providers = await _async_chat_providers()
    initial_model_name = await _async_provider_display_model(providers[0]) if providers else ""

    await ConversationMessage.objects.acreate(
        round=round_obj,
        role="participant",
        content=text,
        language=round_obj.session.language,
        ai_mode_name=round_obj.ai_mode.name_zh,
        model_name=initial_model_name,
    )

    prior_messages = [
        {
            "role": "system",
            "content": build_system_prompt(
                round_obj.session.batch,
                round_obj.ai_mode,
                round_obj.session.language,
            ),
        }
    ]
    async for message in round_obj.conversation_messages.filter(was_interrupted=False).order_by("created_at"):
        role = "assistant" if message.role == "assistant" else "user"
        if message.role in {"assistant", "participant"} and message.content.strip():
            prior_messages.append({"role": role, "content": message.content})

    async def event_stream():
        errors = []
        if not providers:
            errors.append(ImproperlyConfigured(AI_CONFIGURATION_ERROR))

        stream_start = time.monotonic()
        print(f"[ttft] event_stream begin t=0.000s providers={len(providers)} prior_messages={len(prior_messages)}", flush=True)

        for provider in providers:
            model_name = await _async_provider_display_model(provider)
            assistant_message = None
            saved_at = 0

            try:
                gen = async_chat_stream(prior_messages, provider=provider)

                try:
                    first = await gen.__anext__()
                except StopAsyncIteration:
                    first = None

                if first is not None:
                    elapsed = time.monotonic() - stream_start
                    print(f"[ttft] first chunk received t={elapsed:.3f}s model={getattr(provider, '_last_model_name', model_name)} preview={first[:30]!r}", flush=True)
                    model_name = getattr(provider, "_last_model_name", model_name)
                    assistant_message = await ConversationMessage.objects.acreate(
                        round=round_obj,
                        role="assistant",
                        content=first,
                        language=round_obj.session.language,
                        ai_mode_name=round_obj.ai_mode.name_zh,
                        model_name=model_name,
                    )
                    saved_at = time.monotonic()
                    yield _sse_message(first)

                async for chunk in gen:
                    if not chunk:
                        continue
                    if assistant_message is None:
                        model_name = getattr(provider, "_last_model_name", model_name)
                        assistant_message = await ConversationMessage.objects.acreate(
                            round=round_obj,
                            role="assistant",
                            content=chunk,
                            language=round_obj.session.language,
                            ai_mode_name=round_obj.ai_mode.name_zh,
                            model_name=model_name,
                        )
                        saved_at = time.monotonic()
                    else:
                        assistant_message.content += chunk
                        now = time.monotonic()
                        if now - saved_at >= 0.5:
                            await ConversationMessage.objects.filter(pk=assistant_message.pk).aupdate(
                                content=assistant_message.content
                            )
                            saved_at = now
                    yield _sse_message(chunk)
            except Exception as exc:  # pragma: no cover - network failure path.
                errors.append(exc)
                if assistant_message is not None:
                    assistant_message.error_message = str(exc)
                    await ConversationMessage.objects.filter(pk=assistant_message.pk).aupdate(
                        content=assistant_message.content,
                        error_message=assistant_message.error_message,
                    )
                    yield _sse_message(_friendly_chat_error(exc), event="error")
                    return
                continue

            model_name = getattr(provider, "_last_model_name", model_name)
            if assistant_message is None:
                await ConversationMessage.objects.acreate(
                    round=round_obj,
                    role="assistant",
                    content="",
                    language=round_obj.session.language,
                    ai_mode_name=round_obj.ai_mode.name_zh,
                    model_name=model_name,
                )
            else:
                assistant_message.model_name = model_name
                await ConversationMessage.objects.filter(pk=assistant_message.pk).aupdate(
                    content=assistant_message.content,
                    model_name=model_name,
                )
            yield _sse_message("ok", event="done")
            return

        exc = errors[-1] if errors else ImproperlyConfigured(AI_CONFIGURATION_ERROR)
        friendly_message = _friendly_chat_error(exc)
        await ConversationMessage.objects.acreate(
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
def transcribe_debug(request):
    event = request.POST.get("event", "unknown")
    detail = request.POST.get("detail", "")
    print(f"[recorder] {event}: {detail}", flush=True)
    return HttpResponse(status=204)


@login_required
@require_POST
def transcribe(request):
    audio_file = request.FILES.get("audio")
    if not audio_file:
        print("[transcribe] missing audio file", flush=True)
        return HttpResponseBadRequest("audio file is required")
    print(
        (
            "[transcribe] received upload: "
            f"name={audio_file.name} size={audio_file.size} "
            f"content_type={getattr(audio_file, 'content_type', '')} "
            f"model={settings.DEFAULT_TRANSCRIBE_MODEL}"
        ),
        flush=True,
    )
    logger.info(
        "Received transcription upload: name=%s size=%s content_type=%s model=%s",
        audio_file.name,
        audio_file.size,
        getattr(audio_file, "content_type", ""),
        settings.DEFAULT_TRANSCRIBE_MODEL,
    )
    try:
        text = transcribe_audio(audio_file, settings.DEFAULT_TRANSCRIBE_MODEL)
    except ImproperlyConfigured as exc:
        print(f"[transcribe] configuration error: {exc}", flush=True)
        logger.warning("Transcription configuration error: %s", exc)
        return JsonResponse(
            {
                "error": _friendly_transcribe_error(exc),
                "detail": str(exc),
                "model": settings.DEFAULT_TRANSCRIBE_MODEL,
            },
            status=503,
        )
    except Exception as exc:  # pragma: no cover - external provider failure details vary.
        print(f"[transcribe] provider error: {exc}", flush=True)
        logger.exception("Transcription provider call failed")
        return JsonResponse(
            {
                "error": _friendly_transcribe_error(exc),
                "detail": str(exc),
                "model": settings.DEFAULT_TRANSCRIBE_MODEL,
            },
            status=502,
        )
    print(f"[transcribe] success: chars={len(text)}", flush=True)
    return JsonResponse({"text": text, "model": settings.DEFAULT_TRANSCRIBE_MODEL})


@login_required
@require_POST
def interrupt_chat(request, round_id):
    try:
        round_obj = TopicRound.objects.select_related(
            "session", "ai_mode"
        ).get(pk=round_id, session__user=request.user)
    except TopicRound.DoesNotExist:
        raise Http404

    partial_content = request.POST.get("partial_content", "")

    if ConversationMessage.objects.filter(round=round_obj, role="assistant", was_interrupted=True).exists():
        return JsonResponse({"ok": True})

    providers = configured_providers()
    model_name = ""
    if providers:
        key = providers[0].api_keys.filter(is_active=True).order_by("usage_count", "id").first()
        if key:
            model_name = key.default_model_name()
        else:
            model_name = providers[0].model_name

    ConversationMessage.objects.create(
        round=round_obj,
        role="assistant",
        content=partial_content,
        language=round_obj.session.language,
        ai_mode_name=round_obj.ai_mode.name_zh if round_obj.ai_mode else "",
        model_name=model_name,
        was_interrupted=True,
        interrupted_at=timezone.now(),
    )
    return JsonResponse({"ok": True})
