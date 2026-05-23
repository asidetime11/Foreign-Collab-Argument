import json
import random
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.experiments.defaults import DEFAULT_TOPIC_ORDER_INTRO_ZH
from apps.experiments.models import AIMode, ScaleItem

from .comment_identity import comment_avatar_file, comment_display_name
from .forms import AIModeForm, CommentReactionForm, EnglishPaperForm, ScaleForm, TextResponseForm, TopicOrderForm
from .models import CommentReaction, EnglishPaperDraft, EnglishPaperResponse, PostReaction, ScaleResponse, SurveySession, TextResponse
from .services import (
    SESSION_DONE,
    STEP_RESEARCH_CONSENT,
    STEP_TOPIC_ORDER,
    accept_research_consent,
    advance_after_mode,
    complete_round_step,
    complete_english_paper,
    current_round,
    current_step,
    get_or_create_session,
    record_quality_event,
    scale_items_for_step,
    start_current_step,
    submit_topic_order,
)


STEP_META = {
    "consent": {"number": 1, "title": "参与研究授权同意书", "kind": "consent"},
    "topic_order": {"number": 1, "title": "先排一排你最在意的话题", "kind": "sort"},
    "post": {"number": 2, "title": "阅读帖子与评论", "kind": "read"},
    "emotion": {"number": 3, "title": "当前感受", "kind": "mood"},
    "stance_before": {"number": 4, "title": "你的观点", "kind": "stance"},
    "initial_text": {"number": 5, "title": "写下你的想法", "kind": "text"},
    "mode": {"number": 6, "title": "选择对话模式", "kind": "mode"},
    "chat": {"number": 7, "title": "与人工智能对话", "kind": "chat"},
    "ai_eval": {"number": 8, "title": "对人工智能的评价", "kind": "ai_eval"},
    "stance_after": {"number": 9, "title": "再次确认你的观点", "kind": "stance"},
    "final_text": {"number": 10, "title": "写下你的新想法", "kind": "text"},
    "english_paper": {"number": 11, "title": "英文论文写作", "kind": "text"},
    "done": {"number": 12, "title": "已完成，感谢你的参与", "kind": "done"},
}


def _step_context(step):
    meta = STEP_META[step].copy()
    meta["total"] = 12
    meta["label"] = f"第 {meta['number']} 站"
    meta["route"] = range(1, 13)
    return meta


def _localized(material, field, language):
    if language.startswith("en"):
        return material.get(f"{field}_en") or material.get(f"{field}_zh") or ""
    return material.get(f"{field}_zh") or material.get(f"{field}_en") or ""


def _stance_prompt(material, role, language, statement):
    field = f"{role}_prompt"
    custom = _localized(material, field, language)
    if custom:
        return custom
    if role == "agreement":
        if statement:
            return f'你有多大程度上同意"{statement}"这个观点？'
        return "你有多大程度上同意这个观点？"
    return "你对自己上述的观点有多确定？"


def _guard_session(request):
    profile = request.user.participant_profile
    if not profile.batch:
        return None, render(request, "survey/start.html", {"missing_batch": True})
    try:
        return get_or_create_session(request.user, "zh-hans"), None
    except ValueError as exc:
        return None, render(request, "survey/start.html", {"missing_batch": True})


def _current_route(session):
    step = current_step(session)
    if step == STEP_RESEARCH_CONSENT:
        return reverse("survey:consent")
    if step == STEP_TOPIC_ORDER:
        return reverse("survey:topic_order")
    if step == SESSION_DONE:
        return reverse("survey:done")
    if step == SurveySession.STEP_ENGLISH_PAPER:
        return reverse("survey:english_paper")
    if step == "post":
        return reverse("survey:post")
    if step in {"emotion", "stance_before", "ai_eval", "stance_after"}:
        return reverse("survey:scale", args=[step])
    if step in {"initial_text", "final_text"}:
        return reverse("survey:text_response", args=[step])
    if step == "mode":
        return reverse("survey:mode_select")
    if step == "chat":
        return reverse("survey:chat")
    return reverse("survey:start")


def _require_current(session, expected_step):
    if current_step(session) != expected_step:
        return redirect(_current_route(session))
    start_current_step(session)
    return None


def _chat_remaining_seconds(round_obj, minutes):
    total_seconds = max(int(minutes or 0) * 60, 0)
    started_raw = round_obj.step_started_at.get("chat")
    if not started_raw:
        return total_seconds
    started_at = parse_datetime(started_raw)
    if not started_at:
        return total_seconds
    if timezone.is_naive(started_at):
        started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
    elapsed = int((timezone.now() - started_at).total_seconds())
    return max(total_seconds - elapsed, 0)


def _remaining_seconds_from_started(started_raw, total_seconds):
    if not started_raw:
        return total_seconds
    started_at = parse_datetime(started_raw)
    if not started_at:
        return total_seconds
    if timezone.is_naive(started_at):
        started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
    elapsed = int((timezone.now() - started_at).total_seconds())
    return max(total_seconds - elapsed, 0)


def _deadline_timestamp_ms_from_started(started_raw, total_seconds):
    started_at = parse_datetime(started_raw or "")
    if not started_at:
        started_at = timezone.now()
    if timezone.is_naive(started_at):
        started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
    deadline_at = started_at + timezone.timedelta(seconds=total_seconds)
    return int(deadline_at.timestamp() * 1000)


def _round_progress_context(session):
    total = max(session.rounds.count(), len(session.round_order), 1)
    current = min(int(session.current_round_index or 0) + 1, total)
    return {"current_post_number": current, "total_posts": total}


def _common_ctx(session):
    return {
        "batch": session.batch,
        "lang": "en" if session.language.startswith("en") else "zh",
    }


@login_required
def start(request):
    session, response = _guard_session(request)
    if response:
        return response
    return redirect(_current_route(session))


@login_required
def consent(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, STEP_RESEARCH_CONSENT)
    if wrong_step:
        return wrong_step
    lang = "en" if session.language.startswith("en") else "zh"
    if request.method == "POST":
        if request.POST.get("agree") != "on":
            return render(
                request,
                "survey/step_consent.html",
                {
                    "session": session,
                    "batch": session.batch,
                    "lang": lang,
                    "step_meta": _step_context("consent"),
                    "error": "请先勾选同意，再进入下一步。",
                },
            )
        accept_research_consent(session)
        return redirect(_current_route(session))
    return render(request, "survey/step_consent.html", {"session": session, "batch": session.batch, "lang": lang, "step_meta": _step_context("consent")})


@login_required
def topic_order(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, STEP_TOPIC_ORDER)
    if wrong_step:
        return wrong_step
    initial_ids = ",".join(str(item["id"]) for item in session.topic_order_snapshot)
    if request.method == "POST":
        form = TopicOrderForm(request.POST)
        if form.is_valid():
            submit_topic_order(session, form.topic_ids())
            return redirect(_current_route(session))
    else:
        form = TopicOrderForm(initial={"ordered_topic_ids": initial_ids})
    language = session.language
    topics = [
        {
            "id": item["id"],
            "title": _localized(item, "title", language),
            "statement": _localized(item, "statement", language),
        }
        for item in session.topic_order_snapshot
    ]
    return render(
        request,
        "survey/step_topic_order.html",
        {
            "form": form,
            "session": session,
            "topics": topics,
            "step_meta": _step_context("topic_order"),
            "topic_order_intro": session.batch.intro_zh or DEFAULT_TOPIC_ORDER_INTRO_ZH,
            **_common_ctx(session),
        },
    )


@login_required
def post(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, "post")
    if wrong_step:
        return wrong_step
    round_obj = current_round(session)
    comments = round_obj.material_snapshot.get("comments", [])
    if request.method == "POST":
        form = CommentReactionForm(comments, request.POST)
        if form.is_valid():
            PostReaction.objects.create(round=round_obj, reaction=form.cleaned_data.get("post_reaction") or "none")
            for comment in comments:
                reaction = form.cleaned_data.get(f"comment_{comment['id']}") or "none"
                CommentReaction.objects.create(round=round_obj, comment_snapshot_id=comment["id"], reaction=reaction)
            complete_round_step(round_obj, "post")
            return redirect(_current_route(session))
    else:
        form = CommentReactionForm(comments)
    language = session.language
    material = {
        "title": _localized(round_obj.material_snapshot, "title", language),
        "post_body": _localized(round_obj.material_snapshot, "post_body", language),
        "author": comment_display_name(len(comments)),
        "avatar_file": comment_avatar_file(len(comments)),
        "comments": [
            {
                **comment,
                "author": comment_display_name(index),
                "body": comment.get("body_en") if language.startswith("en") and comment.get("body_en") else comment.get("body_zh"),
                "avatar_file": comment_avatar_file(index),
            }
            for index, comment in enumerate(comments)
        ],
    }
    return render(
        request,
        "survey/step_post.html",
        {
            "form": form,
            "round": round_obj,
            "material": material,
            "step_meta": _step_context("post"),
            **_round_progress_context(session),
            **_common_ctx(session),
        },
    )


@login_required
def scale(request, step):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, step)
    if wrong_step:
        return wrong_step
    round_obj = current_round(session)
    items = list(scale_items_for_step(session.batch, step))
    if step in {"stance_before", "stance_after"} and not items:
        items = [
            SimpleNamespace(pk="default-agreement", item_type=ScaleItem.STANCE, stance_role="agreement", label_zh="同意程度", label_en="Agreement", left_label_zh="", left_label_en="", right_label_zh="", right_label_en="", min_value=1, max_value=6),
            SimpleNamespace(pk="default-confidence", item_type=ScaleItem.STANCE, stance_role="confidence", label_zh="确定程度", label_en="Confidence", left_label_zh="", left_label_en="", right_label_zh="", right_label_en="", min_value=1, max_value=6),
        ]
    for idx, item in enumerate(items):
        item.values = range(item.min_value, item.max_value + 1)
        if not hasattr(item, "stance_role") or item.stance_role is None:
            item.stance_role = "agreement" if idx == 0 else "confidence"
    if request.method == "POST":
        form = ScaleForm(items, request.POST)
        if form.is_valid():
            language = session.language
            for item in items:
                label = item.label_en if language.startswith("en") and item.label_en else item.label_zh
                ScaleResponse.objects.create(
                    round=round_obj,
                    step=step,
                    item_type=item.item_type,
                    item_label=label,
                    language=language,
                    min_value=item.min_value,
                    max_value=item.max_value,
                    selected_value=form.cleaned_data[f"item_{item.pk}"],
                )
            complete_round_step(round_obj, step)
            return redirect(_current_route(session))
    else:
        form = ScaleForm(items)
    statement = _localized(round_obj.material_snapshot, "statement", session.language)
    agreement_prompt = _stance_prompt(round_obj.material_snapshot, "agreement", session.language, statement)
    confidence_prompt = _stance_prompt(round_obj.material_snapshot, "confidence", session.language, statement)
    agreement_defaults = ["非常不同意", "不同意", "有点不同意", "有点同意", "同意", "非常同意"]
    confidence_defaults = ["完全不确定", "不确定", "有点不确定", "有点确定", "确定", "非常确定"]
    agreement_labels = [
        getattr(session.batch, f"agreement_label_{i}", "") or agreement_defaults[i - 1]
        for i in range(1, 7)
    ]
    confidence_labels = [
        getattr(session.batch, f"confidence_label_{i}", "") or confidence_defaults[i - 1]
        for i in range(1, 7)
    ]
    return render(
        request,
        "survey/step_scale.html",
        {
            "form": form,
            "items": items,
            "step": step,
            "round": round_obj,
            "statement": statement,
            "agreement_prompt": agreement_prompt,
            "confidence_prompt": confidence_prompt,
            "agreement_labels": agreement_labels,
            "confidence_labels": confidence_labels,
            "step_meta": _step_context(step),
            **_round_progress_context(session),
            **_common_ctx(session),
        },
    )


@login_required
def text_response(request, step):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, step)
    if wrong_step:
        return wrong_step
    round_obj = current_round(session)
    if request.method == "POST":
        form = TextResponseForm(request.POST)
        if form.is_valid():
            final_text = form.cleaned_data["final_text"].strip()
            TextResponse.objects.create(
                round=round_obj,
                step=step,
                final_text=final_text,
                input_method=form.cleaned_data.get("input_method") or "keyboard",
                transcribe_model=form.cleaned_data.get("transcribe_model", ""),
                was_edited=form.cleaned_data.get("was_edited", False),
                word_count=len(final_text.split()) if " " in final_text else len(final_text),
            )
            complete_round_step(round_obj, step)
            return redirect(_current_route(session))
    else:
        form = TextResponseForm(initial={"input_method": "keyboard"})
    language = session.language
    comments = round_obj.material_snapshot.get("comments", [])
    material = {
        "title": _localized(round_obj.material_snapshot, "title", language),
        "post_body": _localized(round_obj.material_snapshot, "post_body", language),
        "author": comment_display_name(len(comments)),
        "avatar_file": comment_avatar_file(len(comments)),
        "comments": [
            {
                **comment,
                "author": comment_display_name(index),
                "body": comment.get("body_en") if language.startswith("en") and comment.get("body_en") else comment.get("body_zh"),
                "avatar_file": comment_avatar_file(index),
            }
            for index, comment in enumerate(comments)
        ],
    }
    return render(
        request,
        "survey/step_text.html",
        {
            "form": form,
            "step": step,
            "round": round_obj,
            "material": material,
            "step_meta": _step_context(step),
            **_round_progress_context(session),
            **_common_ctx(session),
        },
    )


@login_required
def mode_select(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, "mode")
    if wrong_step:
        return wrong_step
    round_obj = current_round(session)
    modes = list(AIMode.objects.filter(batch=session.batch, is_enabled=True))
    random.shuffle(modes)
    if request.method == "POST":
        form = AIModeForm(request.POST)
        if form.is_valid():
            advance_after_mode(round_obj, form.cleaned_data["selected_mode"])
            return redirect(_current_route(session))
    else:
        form = AIModeForm()
    return render(
        request,
        "survey/step_mode.html",
        {
            "form": form,
            "modes": modes,
            "round": round_obj,
            "step_meta": _step_context("mode"),
            **_round_progress_context(session),
            **_common_ctx(session),
        },
    )


@login_required
def chat(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, "chat")
    if wrong_step:
        return wrong_step
    round_obj = current_round(session)
    if request.method == "POST":
        complete_round_step(round_obj, "chat")
        return redirect(_current_route(session))
    chat_messages = round_obj.conversation_messages.filter(role__in=["participant", "assistant"]).order_by("created_at")
    return render(
        request,
        "survey/step_chat.html",
        {
            "round": round_obj,
            "minutes": session.batch.ai_chat_minutes,
            "remaining_seconds": _chat_remaining_seconds(round_obj, session.batch.ai_chat_minutes),
            "chat_messages": chat_messages,
            "step_meta": _step_context("chat"),
            **_round_progress_context(session),
            **_common_ctx(session),
        },
    )


@login_required
def done(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, SESSION_DONE)
    if wrong_step:
        return wrong_step
    language = session.language
    outro = session.batch_snapshot.get("outro_en") if language.startswith("en") else session.batch_snapshot.get("outro_zh")
    return render(request, "survey/done.html", {"session": session, "outro": outro, "step_meta": _step_context("done"), **_common_ctx(session)})


@login_required
@never_cache
def english_paper(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, SurveySession.STEP_ENGLISH_PAPER)
    if wrong_step:
        return wrong_step
    prompt = session.batch.english_paper_prompt or session.batch_snapshot.get("english_paper_prompt", "")
    duration_hours = session.batch.english_paper_duration_hours or session.batch_snapshot.get("english_paper_duration_hours", 24)
    total_seconds = max(int(duration_hours or 0) * 3600, 0)
    remaining_seconds = _remaining_seconds_from_started(
        session.step_started_at.get(SurveySession.STEP_ENGLISH_PAPER),
        total_seconds,
    )
    deadline_at = _deadline_timestamp_ms_from_started(
        session.step_started_at.get(SurveySession.STEP_ENGLISH_PAPER),
        total_seconds,
    )
    draft = EnglishPaperDraft.objects.filter(session=session).first()
    if request.method == "POST":
        form = EnglishPaperForm(request.POST)
        if form.is_valid():
            EnglishPaperResponse.objects.update_or_create(
                session=session,
                defaults={
                    "prompt": prompt,
                    "duration_hours": duration_hours,
                    "paper_text": form.cleaned_data["paper_text"].strip(),
                },
            )
            complete_english_paper(session)
            return redirect(_current_route(session))
    else:
        form = EnglishPaperForm(initial={"paper_text": draft.paper_text if draft else ""})
    return render(
        request,
        "survey/step_english_paper.html",
        {
            "form": form,
            "session": session,
            "prompt": prompt,
            "duration_hours": duration_hours,
            "remaining_seconds": remaining_seconds,
            "deadline_at": deadline_at,
            "draft": draft,
            "step_meta": _step_context("english_paper"),
            **_common_ctx(session),
        },
    )


@login_required
@require_POST
def english_paper_draft(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, SurveySession.STEP_ENGLISH_PAPER)
    if wrong_step:
        return HttpResponseBadRequest("english paper step is not active")
    prompt = session.batch.english_paper_prompt or session.batch_snapshot.get("english_paper_prompt", "")
    duration_hours = session.batch.english_paper_duration_hours or session.batch_snapshot.get("english_paper_duration_hours", 24)
    draft, _created = EnglishPaperDraft.objects.update_or_create(
        session=session,
        defaults={
            "prompt": prompt,
            "duration_hours": duration_hours,
            "paper_text": request.POST.get("paper_text", "").strip(),
        },
    )
    return JsonResponse({"ok": True, "saved_at": timezone.localtime(draft.saved_at).strftime("%H:%M")})


@login_required
@require_POST
def quality_event(request):
    allowed = {"copy", "paste", "cut", "contextmenu", "refresh", "shortcut"}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("invalid json")
    event_type = payload.get("event_type")
    if event_type not in allowed:
        return HttpResponseBadRequest("invalid event")
    record_quality_event(request.user, event_type, payload.get("metadata", {}))
    return JsonResponse({"ok": True})
