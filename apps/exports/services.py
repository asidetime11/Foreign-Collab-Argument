import csv
import io
import zipfile

from openpyxl import Workbook

from apps.accounts.models import ParticipantProfile
from apps.survey.comment_identity import comment_display_name
from apps.survey.models import CommentReaction, ConversationMessage, QualityEvent, ScaleResponse, SurveySession, TextResponse, TopicRound


SECTIONS = {
    "participants": "participants",
    "snapshots": "snapshots",
    "topic_order": "topic_order",
    "rounds": "rounds",
    "comment_reactions": "comment_reactions",
    "scale_responses": "scale_responses",
    "text_responses": "text_responses",
    "conversation": "conversation",
    "quality_events": "quality_events",
}


def participant_rows(batch):
    return [
        {
            "username": profile.user.username,
            "display_name": profile.display_name,
            "region": profile.region,
            "gender": profile.gender,
            "contact": profile.contact,
        }
        for profile in batch.participants.select_related("user")
    ]


def snapshot_rows(batch):
    return [{"username": session.user.username, "batch_snapshot": session.batch_snapshot} for session in batch.sessions.select_related("user")]


def topic_order_rows(batch):
    return [
        {
            "username": session.user.username,
            "initial_order": session.topic_order_snapshot,
            "submitted_order": session.submitted_topic_order,
            "high_topic_id": session.selected_high_topic_id,
            "low_topic_id": session.selected_low_topic_id,
        }
        for session in batch.sessions.select_related("user")
    ]


def round_rows(batch):
    return [
        {
            "username": round_obj.session.user.username,
            "round_type": round_obj.round_type,
            "topic_id": round_obj.topic_id,
            "skipped_ai": round_obj.skipped_ai,
            "completed": round_obj.is_completed,
        }
        for round_obj in _rounds(batch)
    ]


def comment_reaction_rows(batch):
    return [
        {
            "username": reaction.round.session.user.username,
            "round_type": reaction.round.round_type,
            "comment_snapshot_id": reaction.comment_snapshot_id,
            "reaction": reaction.reaction,
        }
        for reaction in _reaction_queryset(batch)
    ]


def scale_response_rows(batch):
    return [
        {
            "username": response.round.session.user.username,
            "step": response.step,
            "item_type": response.item_type,
            "item_label": response.item_label,
            "selected_value": response.selected_value,
        }
        for response in ScaleResponse.objects.filter(round__session__batch=batch).select_related("round__session__user")
    ]


def text_response_rows(batch):
    return [
        {
            "username": response.round.session.user.username,
            "step": response.step,
            "final_text": response.final_text,
            "input_method": response.input_method,
            "word_count": response.word_count,
        }
        for response in TextResponse.objects.filter(round__session__batch=batch).select_related("round__session__user")
    ]


def conversation_rows(batch):
    return [
        {
            "username": message.round.session.user.username,
            "round_type": message.round.round_type,
            "role": message.role,
            "content": message.content,
            "model_name": message.model_name,
        }
        for message in ConversationMessage.objects.filter(round__session__batch=batch).select_related("round__session__user")
    ]


def quality_event_rows(batch):
    return [
        {
            "username": event.user.username,
            "event_type": event.event_type,
            "metadata": event.metadata,
            "created_at": event.created_at.isoformat(),
        }
        for event in QualityEvent.objects.filter(session__batch=batch).select_related("user")
    ]


SECTION_BUILDERS = {
    "participants": participant_rows,
    "snapshots": snapshot_rows,
    "topic_order": topic_order_rows,
    "rounds": round_rows,
    "comment_reactions": comment_reaction_rows,
    "scale_responses": scale_response_rows,
    "text_responses": text_response_rows,
    "conversation": conversation_rows,
    "quality_events": quality_event_rows,
}


def _rounds(batch):
    return TopicRound.objects.filter(session__batch=batch).select_related("session__user")


def _reaction_queryset(batch):
    from apps.survey.models import CommentReaction

    return CommentReaction.objects.filter(round__session__batch=batch).select_related("round__session__user")


def selected_rows(batch, sections):
    return {section: SECTION_BUILDERS[section](batch) for section in sections if section in SECTION_BUILDERS}


def build_excel(batch, sections):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for section, rows in selected_rows(batch, sections).items():
        sheet = workbook.create_sheet(section[:31])
        headers = sorted(rows[0].keys()) if rows else ["empty"]
        sheet.append(headers)
        for row in rows:
            sheet.append([str(row.get(header, "")) for header in headers])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


def _joined_values(values):
    return "\n".join(str(value) for value in values if value not in [None, ""])


def _scale_summary(rounds, step):
    rows = ScaleResponse.objects.filter(round__in=rounds, step=step).order_by("submitted_at", "id")
    return _joined_values(f"{row.item_label}={row.selected_value}" for row in rows)


def _text_for_step(rounds, step):
    rows = TextResponse.objects.filter(round__in=rounds, step=step).order_by("submitted_at", "id")
    return _joined_values(row.final_text for row in rows)


def _conversation_text(rounds):
    messages = ConversationMessage.objects.filter(round__in=rounds).order_by("created_at", "id")
    return _joined_values(f"{message.get_role_display()}：{message.content}" for message in messages if message.content)


def _comment_by_snapshot_id(round_obj, comment_snapshot_id):
    for index, comment in enumerate(round_obj.material_snapshot.get("comments", [])):
        if comment.get("id") == comment_snapshot_id:
            return comment, index
    return {}, None


def _comment_reaction_label(reaction):
    labels = {"like": "赞", "dislike": "踩", "none": "无操作"}
    return labels.get(reaction, reaction)


def build_all_users_excel():
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "用户总表"
    summary_headers = [
        "用户名",
        "称呼/姓名",
        "地区",
        "年龄段",
        "性别",
        "学校/单位类型",
        "教育/职业状态",
        "联系方式",
        "观点排序",
        "感受",
        "观点",
        "AI评价",
        "初始想法",
        "最终想法",
        "与AI对话",
        "开始时间",
        "完成时间",
    ]
    summary_sheet.append(summary_headers)

    conversation_sheet = workbook.create_sheet("AI对话")
    conversation_sheet.append(["用户名", "轮次", "角色", "内容", "AI模式", "模型", "创建时间"])

    reaction_sheet = workbook.create_sheet("评论互动")
    reaction_sheet.append(["用户名", "轮次", "话题ID", "评论ID", "评论作者", "评论内容", "互动", "提交时间"])

    profiles = ParticipantProfile.objects.select_related("user", "batch").order_by("user__username")
    for profile in profiles:
        try:
            session = profile.user.survey_session
        except SurveySession.DoesNotExist:
            session = None
        rounds = list(session.rounds.all()) if session else []
        topic_order = session.submitted_topic_order if session else []
        summary_sheet.append(
            [
                profile.user.username,
                profile.display_name,
                profile.region,
                profile.age_range,
                profile.gender,
                profile.organization_type,
                profile.education_or_work,
                profile.contact,
                str(topic_order),
                _scale_summary(rounds, "emotion"),
                _joined_values([_scale_summary(rounds, "stance_before"), _scale_summary(rounds, "stance_after")]),
                _scale_summary(rounds, "ai_eval"),
                _text_for_step(rounds, "initial_text"),
                _text_for_step(rounds, "final_text"),
                _conversation_text(rounds),
                session.started_at.isoformat() if session else "",
                session.completed_at.isoformat() if session and session.completed_at else "",
            ]
        )
        for message in ConversationMessage.objects.filter(round__in=rounds).select_related("round").order_by("created_at", "id"):
            conversation_sheet.append(
                [
                    profile.user.username,
                    message.round.round_type,
                    message.get_role_display(),
                    message.content,
                    message.ai_mode_name,
                    message.model_name,
                    message.created_at.isoformat(),
                ]
            )
        for reaction in CommentReaction.objects.filter(round__in=rounds).select_related("round").order_by("submitted_at", "id"):
            comment, comment_index = _comment_by_snapshot_id(reaction.round, reaction.comment_snapshot_id)
            reaction_sheet.append(
                [
                    profile.user.username,
                    reaction.round.round_type,
                    reaction.round.topic_id,
                    reaction.comment_snapshot_id,
                    comment_display_name(comment_index),
                    comment.get("body_zh") or comment.get("body_en", ""),
                    _comment_reaction_label(reaction.reaction),
                    reaction.submitted_at.isoformat(),
                ]
            )

    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


def build_csv_zip(batch, sections):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for section, rows in selected_rows(batch, sections).items():
            buffer = io.StringIO()
            headers = sorted(rows[0].keys()) if rows else ["empty"]
            writer = csv.DictWriter(buffer, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({header: row.get(header, "") for header in headers})
            archive.writestr(f"{section}.csv", buffer.getvalue())
    output.seek(0)
    return output.getvalue()
