from io import BytesIO

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.accounts.models import ParticipantProfile
from apps.exports.services import build_all_users_excel

from .models import AIMode, ExperimentBatch, Topic


class PageCopyForm(forms.ModelForm):
    class Meta:
        model = ExperimentBatch
        fields = ["intro_zh"]
        labels = {"intro_zh": "说明内容"}
        widgets = {
            "intro_zh": forms.Textarea(
                attrs={
                    "rows": 8,
                    "class": "copy-textarea",
                    "placeholder": "请按你的真实想法对以下话题排序。提交后不可返回修改。",
                }
            )
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
        "users_url": reverse("research_admin_users"),
        "export_url": reverse("research_admin_export_all"),
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
    return render(request, "admin/research/copy_settings.html", {"title": "第一步说明文字", "form": form})


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
        elif session.completed_at:
            status = "已完成"
            current_step = session.current_session_step
            round_count = session.rounds.count()
            started_at = session.started_at
            completed_at = session.completed_at
        else:
            status = "进行中"
            current_step = session.current_session_step
            round_count = session.rounds.count()
            started_at = session.started_at
            completed_at = None
        rows.append(
            {
                "user": profile.user,
                "display_name": profile.display_name,
                "status": status,
                "current_step": current_step,
                "round_count": round_count,
                "started_at": started_at,
                "completed_at": completed_at,
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
    payload = build_all_users_excel()
    response = HttpResponse(payload, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="all-users-research-data-{stamp}.xlsx"'
    return response
