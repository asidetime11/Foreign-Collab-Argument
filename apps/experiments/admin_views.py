from io import BytesIO

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.accounts.models import ParticipantProfile
from apps.exports.services import build_all_users_csv
from apps.survey.models import CommentReaction, ConversationMessage, EnglishPaperResponse, PostReaction, ScaleResponse, SurveySession, TextResponse

from .models import AIMode, ExperimentBatch, Topic


ROUND_TYPE_LABELS = {
    "high": "高分话题",
    "low": "低分话题",
}

SESSION_STEP_LABELS = {
    "topic_order": "话题排序",
    "round": "话题答题中",
    "english_paper": "英文论文写作",
    "done": "已完成",
}

ROUND_STEP_LABELS = {
    "post": "阅读帖子与评论",
    "emotion": "当前感受量表",
    "stance_before": "AI 对话前观点量表",
    "initial_text": "AI 对话前文字回答",
    "mode": "选择 AI 对话方式",
    "chat": "AI 对话",
    "ai_eval": "AI 回复评价量表",
    "stance_after": "AI 对话后观点量表",
    "final_text": "AI 对话后文字回答",
}

ROUND_STEP_HINTS = {
    "emotion": "记录用户看到帖子后的情绪和思考状态。",
    "stance_before": "记录用户与 AI 对话前对话题的立场。",
    "initial_text": "用户在 AI 对话前写下的开放式想法。",
    "ai_eval": "用户对 AI 回复质量、中立性等方面的评价。",
    "stance_after": "记录用户与 AI 对话后对话题的立场。",
    "final_text": "用户在 AI 对话后写下的最终想法。",
}

REACTION_LABELS = {
    "like": "点赞",
    "dislike": "点踩",
    "none": "未选择",
}

ROLE_LABELS = {
    "participant": "用户",
    "assistant": "AI",
    "system": "系统",
}

INPUT_METHOD_LABELS = {
    "keyboard": "键盘输入",
    "voice": "语音输入",
}


def _display(value, fallback="-"):
    return value if value not in (None, "") else fallback


def _round_label(round_obj):
    return ROUND_TYPE_LABELS.get(round_obj.round_type, round_obj.round_type)


def _round_topic_title(round_obj, topic_titles):
    snapshot = round_obj.material_snapshot or {}
    return (
        snapshot.get("title_zh")
        or snapshot.get("title_en")
        or topic_titles.get(round_obj.topic_id)
        or f"话题 #{round_obj.topic_id}"
    )


def _step_label(step):
    return ROUND_STEP_LABELS.get(step, step)


class PageCopyForm(forms.ModelForm):
    class Meta:
        model = ExperimentBatch
        fields = ["intro_zh", "english_paper_prompt", "english_paper_duration_hours"]
        labels = {
            "intro_zh": "说明内容",
            "english_paper_prompt": "英文论文要求说明",
            "english_paper_duration_hours": "英文论文时长",
        }
        widgets = {
            "intro_zh": forms.Textarea(
                attrs={
                    "rows": 8,
                    "class": "copy-textarea",
                    "placeholder": "请按你的真实想法对以下话题排序。提交后不可返回修改。",
                }
            ),
            "english_paper_prompt": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "copy-textarea",
                    "placeholder": "Write an English argumentative essay based on the discussion you completed.",
                }
            ),
        }


class BulkRegisterForm(forms.Form):
    initial_password = forms.CharField(
        label="初始密码",
        min_length=5,
        widget=forms.PasswordInput(
            attrs={
                "class": "bulk-input",
                "autocomplete": "new-password",
                "placeholder": "至少 5 位",
            }
        ),
    )
    usernames = forms.CharField(
        label="用户名列表",
        help_text="每行一个用户名。可先导出 Excel 留档，再确认创建账号。",
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "class": "bulk-textarea",
                "placeholder": "student001\nstudent002\nstudent003",
            }
        ),
    )

    def clean_usernames(self):
        raw = self.cleaned_data["usernames"]
        usernames = [line.strip() for line in raw.splitlines() if line.strip()]
        if not usernames:
            raise forms.ValidationError("请至少输入一个用户名。")
        duplicates = sorted({name for name in usernames if usernames.count(name) > 1})
        if duplicates:
            raise forms.ValidationError(f"用户名重复：{', '.join(duplicates)}")
        existing = set(User.objects.filter(username__in=usernames).values_list("username", flat=True))
        if existing:
            raise forms.ValidationError(f"用户名已存在：{', '.join(sorted(existing))}")
        return usernames


def default_batch():
    batch = ExperimentBatch.objects.filter(is_active=True).order_by("id").first()
    if batch:
        return batch
    batch = ExperimentBatch.objects.order_by("id").first()
    if batch:
        return batch
    return ExperimentBatch.objects.create(name="默认实验", is_active=True)


def _parse_started_at(raw_value):
    if not raw_value:
        return None
    started_at = parse_datetime(raw_value)
    if not started_at:
        return None
    if timezone.is_naive(started_at):
        started_at = timezone.make_aware(started_at, timezone.get_current_timezone())
    return started_at


def _format_duration(seconds):
    seconds = max(int(seconds or 0), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def english_paper_countdown(session):
    if not session:
        return "-"
    started_at = _parse_started_at(session.step_started_at.get(SurveySession.STEP_ENGLISH_PAPER))
    if not started_at:
        return "未开始"
    duration_hours = (
        getattr(session.batch, "english_paper_duration_hours", None)
        or session.batch_snapshot.get("english_paper_duration_hours")
        or 24
    )
    total_seconds = int(duration_hours) * 3600
    elapsed = int((timezone.now() - started_at).total_seconds())
    return _format_duration(max(total_seconds - elapsed, 0))


@staff_member_required
def dashboard(request):
    batch = default_batch()
    user_count = batch.participants.count()
    completed_count = batch.sessions.filter(completed_at__isnull=False).count()
    context = {
        "title": "研究管理台",
        "batch": batch,
        "topic_count": Topic.objects.filter(batch=batch).count(),
        "ai_mode_count": AIMode.objects.filter(batch=batch).count(),
        "user_count": user_count,
        "completed_count": completed_count,
        "copy_url": reverse("research_admin_copy"),
        "topics_url": reverse("admin:experiments_topic_changelist"),
        "ai_modes_url": reverse("admin:experiments_aimode_changelist"),
        "system_api_url": reverse("admin:experiments_systemapiconfig_changelist"),
        "llm_providers_url": reverse("admin:experiments_llmprovider_changelist"),
        "users_url": reverse("research_admin_users"),
    }
    return render(request, "admin/research/dashboard.html", context)


@staff_member_required
def copy_settings(request):
    batch = default_batch()
    if request.method == "POST":
        form = PageCopyForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            return redirect("research_admin_dashboard")
    else:
        form = PageCopyForm(instance=batch)
    return render(request, "admin/research/copy_settings.html", {"title": "说明文字", "form": form})


@staff_member_required
def user_records(request):
    batch = default_batch()
    profiles = (
        ParticipantProfile.objects.filter(batch=batch)
        .select_related("user", "user__survey_session")
        .prefetch_related("user__survey_session__rounds")
        .order_by("user__username")
    )
    rows = []
    for profile in profiles:
        session = getattr(profile.user, "survey_session", None)
        if session is None:
            status = "未开始"
            current_step = "-"
            round_count = 0
            started_at = None
            completed_at = None
            paper_countdown = "-"
        elif session.completed_at:
            status = "已完成"
            current_step = session.current_session_step
            round_count = session.rounds.count()
            started_at = session.started_at
            completed_at = session.completed_at
            paper_countdown = "已提交"
        else:
            status = "进行中"
            current_step = session.current_session_step
            round_count = session.rounds.count()
            started_at = session.started_at
            completed_at = None
            paper_countdown = english_paper_countdown(session)
        rows.append(
            {
                "user": profile.user,
                "display_name": profile.display_name,
                "status": status,
                "current_step": current_step,
                "round_count": round_count,
                "started_at": started_at,
                "completed_at": completed_at,
                "paper_countdown": paper_countdown,
                "can_delete": not profile.user.is_staff and not profile.user.is_superuser,
            }
        )
    context = {
        "title": "用户数据",
        "rows": rows,
        "idle_count": sum(1 for row in rows if row["status"] == "未开始"),
        "completed_count": sum(1 for row in rows if row["status"] == "已完成"),
    }
    return render(request, "admin/research/user_records.html", context)


@staff_member_required
def user_detail(request, user_id):
    batch = default_batch()
    profile = get_object_or_404(
        ParticipantProfile.objects.select_related("user", "batch"),
        user_id=user_id,
        batch=batch,
    )
    session = getattr(profile.user, "survey_session", None)
    rounds = list(session.rounds.all()) if session else []
    topic_titles = {
        topic.pk: topic.title_zh or topic.title_en
        for topic in Topic.objects.filter(batch=batch, pk__in=[round_obj.topic_id for round_obj in rounds])
    }
    scale_responses = ScaleResponse.objects.filter(round__in=rounds).select_related("round").order_by("submitted_at", "id")
    text_responses = TextResponse.objects.filter(round__in=rounds).select_related("round").order_by("submitted_at", "id")
    conversation_messages = ConversationMessage.objects.filter(round__in=rounds).select_related("round").order_by("created_at", "id")
    post_reactions = PostReaction.objects.filter(round__in=rounds).select_related("round").order_by("submitted_at", "id")
    comment_reactions = CommentReaction.objects.filter(round__in=rounds).select_related("round").order_by("submitted_at", "id")
    scale_rows = [
        {
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "step_label": _step_label(item.step),
            "step_hint": ROUND_STEP_HINTS.get(item.step, ""),
            "item_label": item.item_label,
            "value": item.selected_value,
            "range": f"{item.min_value}-{item.max_value}",
            "submitted_at": item.submitted_at,
        }
        for item in scale_responses
    ]
    text_rows = [
        {
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "step_label": _step_label(item.step),
            "step_hint": ROUND_STEP_HINTS.get(item.step, ""),
            "word_count": item.word_count,
            "input_method": INPUT_METHOD_LABELS.get(item.input_method, item.input_method),
            "was_edited": item.was_edited,
            "content": item.final_text,
            "submitted_at": item.submitted_at,
        }
        for item in text_responses
    ]
    interaction_rows = [
        {
            "type": "帖子",
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "target": _round_topic_title(item.round, topic_titles),
            "reaction": REACTION_LABELS.get(item.reaction, item.reaction),
            "submitted_at": item.submitted_at,
        }
        for item in post_reactions
    ] + [
        {
            "type": "评论",
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "target": f"评论 #{item.comment_snapshot_id}",
            "reaction": REACTION_LABELS.get(item.reaction, item.reaction),
            "submitted_at": item.submitted_at,
        }
        for item in comment_reactions
    ]
    conversation_rows = [
        {
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "role": ROLE_LABELS.get(item.role, item.get_role_display()),
            "content": item.content,
            "model_name": item.model_name,
            "error_message": item.error_message,
            "created_at": item.created_at,
        }
        for item in conversation_messages
    ]
    context = {
        "title": f"用户数据 - {profile.user.username}",
        "profile": profile,
        "session": session,
        "rounds": rounds,
        "current_step_label": SESSION_STEP_LABELS.get(session.current_session_step, session.current_session_step) if session else "-",
        "paper_countdown": english_paper_countdown(session),
        "scale_rows": scale_rows,
        "text_rows": text_rows,
        "interaction_rows": interaction_rows,
        "conversation_rows": conversation_rows,
        "english_paper": EnglishPaperResponse.objects.filter(session=session).first() if session else None,
    }
    return render(request, "admin/research/user_detail.html", context)


def deletable_participants():
    return User.objects.filter(
        participant_profile__batch=default_batch(),
        is_staff=False,
        is_superuser=False,
    )


@staff_member_required
@require_POST
def delete_user(request, user_id):
    queryset = deletable_participants().filter(pk=user_id)
    user_count = queryset.count()
    queryset.delete()
    if user_count:
        messages.success(request, "已删除 1 个参与者账号。")
    else:
        messages.warning(request, "没有可删除的参与者账号。")
    return redirect("research_admin_users")


@staff_member_required
@require_POST
def delete_users(request):
    user_ids = request.POST.getlist("user_ids")
    queryset = deletable_participants().filter(pk__in=user_ids)
    user_count = queryset.count()
    queryset.delete()
    if user_count:
        messages.success(request, f"已删除 {user_count} 个参与者账号。")
    else:
        messages.warning(request, "没有可删除的参与者账号。")
    return redirect("research_admin_users")


@staff_member_required
def bulk_register(request):
    if request.method == "POST":
        form = BulkRegisterForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data["initial_password"]
            usernames = form.cleaned_data["usernames"]
            stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
            if request.POST.get("action") == "export":
                payload = build_bulk_register_excel(request, usernames, password)
                response = HttpResponse(
                    payload,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = f'attachment; filename="participant-accounts-{stamp}.xlsx"'
                return response
            batch = default_batch()
            for username in usernames:
                user = User.objects.create_user(username=username, password=password)
                user.participant_profile.batch = batch
                user.participant_profile.save(update_fields=["batch"])
            messages.success(request, f"已创建 {len(usernames)} 个参与者账号。")
            return redirect("research_admin_users")
    else:
        form = BulkRegisterForm()
    return render(request, "admin/research/bulk_register.html", {"title": "批量注册新用户", "form": form})


def build_bulk_register_excel(request, usernames, password):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "参与者账号"
    headers = ["用户名", "初始密码", "登录地址", "生成时间"]
    sheet.append(headers)
    login_url = request.build_absolute_uri(reverse("login"))
    created_at = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    for username in usernames:
        sheet.append([username, password, login_url, created_at])

    header_fill = PatternFill("solid", fgColor="DFF7EE")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="172033")
        cell.fill = header_fill
    widths = [22, 20, 42, 22]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


@staff_member_required
def export_all(request):
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    payload = build_all_users_csv()
    response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="all-users-research-data-{stamp}.csv"'
    return response
