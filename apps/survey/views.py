import json
import random
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.views.decorators.http import require_POST

from apps.experiments.models import AIMode, ScaleItem

from .forms import AIModeForm, CommentReactionForm, ScaleForm, TextResponseForm, TopicOrderForm
from .models import CommentReaction, ScaleResponse, SurveySession, TextResponse
from .services import (
    SESSION_DONE,
    STEP_TOPIC_ORDER,
    advance_after_mode,
    complete_round_step,
    current_round,
    current_step,
    get_or_create_session,
    record_quality_event,
    scale_items_for_step,
    start_current_step,
    submit_topic_order,
)


def _localized(material, field, language):
    if language.startswith("en"):
        return material.get(f"{field}_en") or material.get(f"{field}_zh") or ""
    return material.get(f"{field}_zh") or material.get(f"{field}_en") or ""


def _guard_session(request):
    profile = request.user.participant_profile
    if not profile.has_required_display_name:
        return None, redirect("accounts:profile_prompt")
    if not profile.batch:
        return None, render(request, "survey/start.html", {"missing_batch": True})
    try:
        return get_or_create_session(request.user, get_language()), None
    except ValueError as exc:
        if str(exc) == "missing_display_name":
            return None, redirect("accounts:profile_prompt")
        return None, render(request, "survey/start.html", {"missing_batch": True})


def _current_route(session):
    step = current_step(session)
    if step == STEP_TOPIC_ORDER:
        return reverse("survey:topic_order")
    if step == SESSION_DONE:
        return reverse("survey:done")
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


@login_required
def start(request):
    session, response = _guard_session(request)
    if response:
        return response
    return redirect(_current_route(session))


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
    language = get_language()
    topics = [
        {
            "id": item["id"],
            "title": _localized(item, "title", language),
            "statement": _localized(item, "statement", language),
        }
        for item in session.topic_order_snapshot
    ]
    return render(request, "survey/step_topic_order.html", {"form": form, "session": session, "topics": topics})


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
            for comment in comments:
                reaction = form.cleaned_data.get(f"comment_{comment['id']}") or "none"
                CommentReaction.objects.create(round=round_obj, comment_snapshot_id=comment["id"], reaction=reaction)
            complete_round_step(round_obj, "post")
            return redirect(_current_route(session))
    else:
        form = CommentReactionForm(comments)
    language = get_language()
    material = {
        "title": _localized(round_obj.material_snapshot, "title", language),
        "post_body": _localized(round_obj.material_snapshot, "post_body", language),
        "comments": [
            {
                **comment,
                "body": comment.get("body_en") if language.startswith("en") and comment.get("body_en") else comment.get("body_zh"),
            }
            for comment in comments
        ],
    }
    return render(request, "survey/step_post.html", {"form": form, "round": round_obj, "material": material})


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
            SimpleNamespace(pk=-1, item_type=ScaleItem.STANCE, label_zh="我同意该观点", label_en="I agree with this view", min_value=1, max_value=7),
            SimpleNamespace(pk=-2, item_type=ScaleItem.STANCE, label_zh="我对判断有把握", label_en="I am certain about my judgment", min_value=1, max_value=7),
        ]
    if request.method == "POST":
        form = ScaleForm(items, request.POST)
        if form.is_valid():
            language = get_language()
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
    return render(request, "survey/step_scale.html", {"form": form, "items": items, "step": step, "round": round_obj})


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
    return render(request, "survey/step_text.html", {"form": form, "step": step, "round": round_obj})


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
    return render(request, "survey/step_mode.html", {"form": form, "modes": modes, "round": round_obj})


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
    return render(request, "survey/step_chat.html", {"round": round_obj, "minutes": session.batch.ai_chat_minutes})


@login_required
def done(request):
    session, response = _guard_session(request)
    if response:
        return response
    wrong_step = _require_current(session, SESSION_DONE)
    if wrong_step:
        return wrong_step
    language = get_language()
    outro = session.batch_snapshot.get("outro_en") if language.startswith("en") else session.batch_snapshot.get("outro_zh")
    return render(request, "survey/done.html", {"session": session, "outro": outro})


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
