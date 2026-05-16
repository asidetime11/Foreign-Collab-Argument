import json
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ParticipantProfile
from apps.experiments.models import AIMode, ExperimentBatch, ScaleItem, Topic
from apps.survey.models import CommentReaction, ConversationMessage, QualityEvent, SurveySession
from apps.survey.services import current_step, get_or_create_session, submit_topic_order


class SurveyStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("p001", password="pass")
        self.batch = ExperimentBatch.objects.create(name="批次 A")
        self.user.participant_profile.display_name = "参与者"
        self.user.participant_profile.batch = self.batch
        self.user.participant_profile.save()
        for index in range(3):
            Topic.objects.create(
                batch=self.batch,
                title_zh=f"话题 {index}",
                title_en=f"Topic {index}",
                position=index,
            )

    def test_starting_session_snapshots_enabled_topics(self):
        session = get_or_create_session(self.user)

        self.assertEqual(len(session.topic_order_snapshot), 3)
        self.assertEqual(current_step(session), "topic_order")

    def test_existing_session_language_is_kept_in_chinese(self):
        SurveySession.objects.create(
            user=self.user,
            batch=self.batch,
            language="en",
            batch_snapshot={},
            topic_order_snapshot=[],
        )

        session = get_or_create_session(self.user)

        self.assertEqual(session.language, "zh-hans")

    def test_topic_order_selects_high_low_and_locks_step(self):
        session = get_or_create_session(self.user)
        ids = [item["id"] for item in session.topic_order_snapshot]

        submit_topic_order(session, ids)
        session.refresh_from_db()

        self.assertEqual(session.selected_high_topic_id, ids[0])
        self.assertEqual(session.selected_low_topic_id, ids[-1])
        self.assertEqual(session.rounds.count(), 2)
        with self.assertRaises(PermissionError):
            submit_topic_order(session, ids)


class SurveyViewTests(TestCase):
    def create_ready_user(self, username="participant", batch=None):
        user = User.objects.create_user(username, password="pass")
        if batch is None:
            batch = ExperimentBatch.objects.create(name="批次 A", intro_zh="请按照你的真实想法排序。", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        return user, batch

    def create_round_for_step(self, step, username="participant"):
        user, batch = self.create_ready_user(username=username)
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        round_obj = session.rounds.create(
            round_type="high",
            topic_id=1,
            current_step=step,
            material_snapshot={
                "title_zh": "话题",
                "post_body_zh": "帖子正文",
                "statement_zh": "这是一个需要判断的观点",
                "comments": [
                    {
                        "id": 1,
                        "author": "参与者 A",
                        "avatar_seed": "a",
                        "relative_time": "刚刚",
                        "like_count": 2,
                        "body_zh": "评论正文",
                    }
                ],
            },
        )
        self.client.force_login(user)
        return user, batch, session, round_obj

    def test_anonymous_user_redirects_to_login(self):
        response = self.client.get(reverse("survey:start"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_missing_display_name_redirects_to_prompt(self):
        user = User.objects.create_user("p002", password="pass")
        self.client.force_login(user)

        response = self.client.get(reverse("survey:start"))

        self.assertRedirects(response, reverse("accounts:profile_prompt"))

    def test_missing_batch_shows_message(self):
        user = User.objects.create_user("p003", password="pass")
        user.participant_profile.display_name = "参与者"
        user.participant_profile.save()
        self.client.force_login(user)

        response = self.client.get(reverse("survey:start"))

        self.assertContains(response, "尚未分配实验批次")

    def test_quality_event_endpoint_records_event(self):
        user = User.objects.create_user("p004", password="pass")
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = ExperimentBatch.objects.create(name="批次 A")
        user.participant_profile.save()
        self.client.force_login(user)

        response = self.client.post(
            reverse("survey:quality_event"),
            data=json.dumps({"event_type": "copy", "metadata": {"key": "c"}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(QualityEvent.objects.filter(user=user, event_type="copy").count(), 1)

    def test_participant_pages_use_chinese_task_shell(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "协同论证平台")
        self.assertNotContains(response, 'class="brand-mark"')
        self.assertNotContains(response, "观点小任务")
        self.assertNotContains(response, "English")
        self.assertNotContains(response, 'name="language"')

    def test_topic_order_page_has_playful_chinese_step_context(self):
        user, batch = self.create_ready_user(username="p_topic")
        batch.intro_zh = (
            "我们正在进行一项关于中国青少年的研究，希望了解高中生们对各种复杂问题的看法，"
            "十分需要你的帮助。"
        )
        batch.save(update_fields=["intro_zh"])
        for index in range(10):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))

        self.assertContains(response, "第 1 站 / 共 11 站")
        self.assertContains(response, "先排一排你最在意的话题")
        self.assertContains(response, "我们正在进行一项关于中国青少年的研究")
        self.assertContains(response, "从上到下：最重要 → 最不重要")
        self.assertContains(response, "确认排序")
        self.assertContains(response, "提交后将进入下一站，排序不能返回修改。")
        self.assertNotContains(response, "排序已完成")
        self.assertNotContains(response, "10 / 10")
        self.assertNotContains(response, "提交排序")

    def test_topic_order_intro_uses_admin_latest_batch_copy(self):
        user, batch = self.create_ready_user(username="p_topic_admin_copy")
        batch.intro_zh = "旧说明"
        batch.save(update_fields=["intro_zh"])
        for index in range(3):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        get_or_create_session(user)

        batch.intro_zh = "管理员刚刚修改的小字说明"
        batch.save(update_fields=["intro_zh"])
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))

        self.assertContains(response, "管理员刚刚修改的小字说明")
        self.assertNotContains(response, "旧说明")

    def test_topic_order_page_renders_ranked_cards_and_controls(self):
        user, batch = self.create_ready_user(username="p_sort")
        for index in range(10):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))

        self.assertContains(response, 'class="topic-card"', count=10)
        self.assertContains(response, 'class="drag-handle"', count=10)
        self.assertContains(response, 'class="topic-content"', count=10)
        self.assertContains(response, 'data-move="up"')
        self.assertContains(response, 'data-move="down"')
        self.assertContains(response, 'name="ordered_topic_ids"')

    def test_topic_order_dragging_has_clear_feedback_and_autoscroll(self):
        user, batch = self.create_ready_user(username="p_sort_drag")
        for index in range(10):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "topic-order.js").read_text(encoding="utf-8")
        stylesheet = (Path(settings.BASE_DIR) / "static" / "survey" / "css" / "site.css").read_text(encoding="utf-8")
        dragover_block = script.split('list.addEventListener("dragover"', 1)[1].split('list.addEventListener("dragleave"', 1)[0]

        self.assertContains(response, 'data-drag-status')
        self.assertIn("function updateAutoScroll", script)
        self.assertIn("window.scrollBy", script)
        self.assertIn('document.addEventListener("dragover"', script)
        self.assertIn('document.addEventListener("drop"', script)
        self.assertIn("let dragOverTarget = null", script)
        self.assertIn("setDragOver(target)", dragover_block)
        # sync() is now called during dragover for real-time number updates
        self.assertIn("sync();", dragover_block)
        self.assertIn("dragging-active", script)
        self.assertIn("drag-over", script)
        self.assertIn(".topic-list.dragging-active", stylesheet)
        self.assertIn(".topic-card.drag-over", stylesheet)

    def test_post_page_renders_optional_like_dislike_controls(self):
        self.create_round_for_step("post", username="p_post")

        response = self.client.get(reverse("survey:post"))

        self.assertContains(response, "阅读帖子与评论")
        self.assertContains(response, 'type="hidden" name="comment_1" value="none"')
        self.assertContains(response, 'class="reaction-button"', count=2)
        self.assertContains(response, 'data-reaction="like"')
        self.assertContains(response, 'data-reaction="dislike"')
        self.assertContains(response, 'aria-label="赞 小兔 的评论"')
        self.assertContains(response, 'aria-label="踩 小兔 的评论"')
        self.assertContains(response, 'class="avatar avatar-small"')
        self.assertContains(response, "survey/img/avatar")
        self.assertContains(response, "survey/img/like.png")
        self.assertContains(response, "survey/img/dislike.png")
        # New design has 4 reaction-icon instances: 2 in post-actions (emoji), 2 in comments (img)
        self.assertContains(response, 'class="reaction-icon"', count=4)
        self.assertContains(response, "survey/js/reactions.js")
        self.assertNotContains(response, "dicebear.com")
        self.assertNotContains(response, 'class="comic-thumb')
        # New design shows emoji thumbs in post-actions
        self.assertContains(response, "👍")
        self.assertContains(response, "👎")
        self.assertNotContains(response, "不选择")
        self.assertNotContains(response, 'type="radio"')
        self.assertNotContains(response, 'class="reaction-choice"')

    def test_post_page_rotates_comment_avatars_without_repeating_first_three(self):
        user, batch, session, round_obj = self.create_round_for_step("post", username="p_post_avatars")
        round_obj.material_snapshot["comments"] = [
            {
                "id": index,
                "author": f"用户 {index}",
                "avatar_seed": "same-kind-of-seed",
                "relative_time": "刚刚",
                "like_count": 10,
                "body_zh": f"评论 {index}",
            }
            for index in [1, 2, 3]
        ]
        round_obj.save(update_fields=["material_snapshot"])

        response = self.client.get(reverse("survey:post"))
        content = response.content.decode("utf-8")

        avatar_files = re.findall(r"survey/img/(avatar\d+\.png)", content)
        self.assertEqual(len(avatar_files), 3)
        self.assertEqual(len(set(avatar_files)), 3)
        self.assertNotIn("avatar4.png", avatar_files)

    def test_post_page_uses_avatar_based_comment_names(self):
        user, batch, session, round_obj = self.create_round_for_step("post", username="p_post_avatar_names")
        round_obj.material_snapshot["comments"] = [
            {
                "id": 1,
                "author": "周明",
                "avatar_seed": "a",
                "relative_time": "刚刚",
                "like_count": 20,
                "body_zh": "评论 1",
            },
            {
                "id": 2,
                "author": "周明",
                "avatar_seed": "b",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 2",
            },
            {
                "id": 3,
                "author": "周明",
                "avatar_seed": "c",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 3",
            },
            {
                "id": 4,
                "author": "周明",
                "avatar_seed": "d",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 4",
            },
            {
                "id": 5,
                "author": "周明",
                "avatar_seed": "e",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 5",
            },
            {
                "id": 6,
                "author": "周明",
                "avatar_seed": "f",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 6",
            },
            {
                "id": 7,
                "author": "周明",
                "avatar_seed": "g",
                "relative_time": "刚刚",
                "like_count": 18,
                "body_zh": "评论 7",
            },
        ]
        round_obj.save(update_fields=["material_snapshot"])

        response = self.client.get(reverse("survey:post"))
        content = response.content.decode("utf-8")

        for name in ["小兔", "小鸭", "小狐", "小狮", "小橙", "小鹅", "小兔 2"]:
            self.assertContains(response, f'<span class="username">{name}</span>', html=True)
        self.assertNotIn("avatar4.png", content)
        self.assertNotContains(response, '<span class="username">周明</span>', html=True)
        self.assertNotContains(response, '<span class="username">周明 2</span>', html=True)

    def test_post_page_saves_comment_interactions(self):
        user, batch, session, round_obj = self.create_round_for_step("post", username="p_post_save_reaction")

        response = self.client.post(reverse("survey:post"), {"comment_1": "like"})

        self.assertEqual(response.status_code, 302)
        reaction = CommentReaction.objects.get(round=round_obj, comment_snapshot_id=1)
        self.assertEqual(reaction.reaction, "like")

    def test_post_styles_use_frameless_small_reaction_icons(self):
        stylesheet = (Path(settings.BASE_DIR) / "static" / "survey" / "css" / "site.css").read_text(encoding="utf-8")

        self.assertIn(".comment-card .reaction-button", stylesheet)
        self.assertIn("width: 30px", stylesheet)
        self.assertIn("border: 0", stylesheet)
        self.assertIn("background: transparent", stylesheet)
        self.assertIn("box-shadow: none", stylesheet)
        self.assertIn("outline: 0", stylesheet)
        self.assertIn("width: 22px", stylesheet)

    def test_scale_page_renders_clickable_slider_controls(self):
        self.create_round_for_step("stance_before", username="p_scale")

        response = self.client.get(reverse("survey:scale", args=["stance_before"]))

        self.assertContains(response, "你的观点")
        # New simplified slider structure
        self.assertContains(response, 'class="scale-slider"')
        self.assertContains(response, 'type="range"')
        self.assertContains(response, 'min="1"')
        self.assertContains(response, 'max="7"')
        self.assertContains(response, 'class="rating-value"')
        # Check for hidden inputs with correct names (order may vary)
        self.assertContains(response, 'name="item_default-agreement"')
        self.assertContains(response, 'name="item_default-confidence"')
        self.assertContains(response, 'class="soft-alert"')
        self.assertContains(response, 'type="hidden"')
        # New design has fixed number labels with data-value attributes
        self.assertContains(response, 'data-value="1"')
        self.assertContains(response, 'class="slider-numbers"')
        # Progress bar now uses CSS pseudo-element (::before) instead of separate div
        # Old elements removed
        self.assertNotContains(response, "未选择")
        self.assertNotContains(response, 'class="rating-readout"')
        self.assertNotContains(response, 'class="slider-track-fill"')



    def test_rating_script_prompts_gently_before_incomplete_submit(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "rating.js").read_text(encoding="utf-8")

        self.assertIn('form.addEventListener("submit"', script)
        self.assertIn('请先完成所有滑杆，再继续。', script)
        self.assertIn('event.preventDefault()', script)

    def test_text_response_page_renders_note_and_no_paste_marker(self):
        self.create_round_for_step("initial_text", username="p_text")

        response = self.client.get(reverse("survey:text_response", args=["initial_text"]))

        self.assertContains(response, "写下你的想法")
        self.assertContains(response, "把你现在想到的写下来就好")
        self.assertContains(response, "保存想法")
        self.assertContains(response, 'data-no-paste="true"')
        self.assertNotContains(response, "我编辑过转写文本")
        self.assertNotContains(response, 'name="was_edited"')

    def test_recorder_appends_transcription_after_existing_text(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "recorder.js").read_text(encoding="utf-8")

        self.assertIn("function appendTranscription", script)
        self.assertIn("textarea.value = current ? `${current}\\n${text}` : text", script)
        self.assertNotIn("textarea.value = payload.text", script)

    def test_mode_page_renders_mode_cards_with_skip_last(self):
        user, batch, session, round_obj = self.create_round_for_step("mode", username="p_mode")
        long_prompt = "提出一个不同角度，帮助我看到当前观点背后可能被忽略的理由和反例。"
        AIMode.objects.create(batch=batch, name_zh="提出不同观点", prompt_zh=long_prompt)
        AIMode.objects.create(batch=batch, name_zh="支持我的观点", prompt_zh="补充支持理由。")

        response = self.client.get(reverse("survey:mode_select"))
        content = response.content.decode()

        self.assertContains(response, "选择对话模式")
        self.assertContains(response, 'class="mode-card"')
        self.assertContains(response, 'class="mode-description"')
        self.assertContains(response, long_prompt)
        self.assertNotContains(response, "忽略的理由和反例…")
        self.assertLess(content.rfind('value="skip"'), content.rfind("</form>"))
        self.assertContains(response, "跳过")

    def test_mode_description_styles_show_full_left_aligned_copy(self):
        stylesheet = (Path(settings.BASE_DIR) / "static" / "survey" / "css" / "site.css").read_text(encoding="utf-8")

        self.assertIn(".mode-description", stylesheet)
        self.assertIn("text-align: left", stylesheet)
        self.assertIn("white-space: normal", stylesheet)
        self.assertIn("overflow: visible", stylesheet)

    def test_chat_page_renders_chinese_game_chat_ui(self):
        user, batch, session, round_obj = self.create_round_for_step("chat", username="p_chat")
        batch.ai_chat_minutes = 5
        batch.save(update_fields=["ai_chat_minutes"])

        response = self.client.get(reverse("survey:chat"))

        self.assertContains(response, "与人工智能对话")
        self.assertContains(response, "剩余时间")
        self.assertContains(response, "完成这轮对话")
        self.assertContains(response, 'data-chat-status')
        self.assertContains(response, 'data-no-paste="true"')

    def test_chat_page_restores_saved_messages_after_refresh(self):
        user, batch, session, round_obj = self.create_round_for_step("chat", username="p_chat_history")
        ConversationMessage.objects.create(round=round_obj, role="participant", content="你好", language="zh-hans")
        ConversationMessage.objects.create(round=round_obj, role="assistant", content="**你好**\n\n- 可以聊这个", language="zh-hans")

        response = self.client.get(reverse("survey:chat"))

        self.assertContains(response, 'data-chat-role="participant"')
        self.assertContains(response, 'data-chat-role="assistant"')
        self.assertContains(response, "你好")
        self.assertContains(response, "**你好**")
        self.assertContains(response, 'data-markdown-source')

    def test_chat_page_restores_error_message_as_friendly_text(self):
        user, batch, session, round_obj = self.create_round_for_step("chat", username="p_chat_error_history")
        ConversationMessage.objects.create(
            round=round_obj,
            role="assistant",
            content="",
            language="zh-hans",
            error_message="list index out of range",
        )

        response = self.client.get(reverse("survey:chat"))

        self.assertContains(response, "暂时没有收到稳定回复，请稍后再试一次。")
        self.assertContains(response, 'class="bubble assistant error"')
        self.assertNotContains(response, "list index out of range")
        self.assertNotContains(response, "ConversationMessage object")

    def test_chat_page_uses_persisted_remaining_seconds_after_refresh(self):
        user, batch, session, round_obj = self.create_round_for_step("chat", username="p_chat_time")
        batch.ai_chat_minutes = 5
        batch.save(update_fields=["ai_chat_minutes"])
        round_obj.step_started_at["chat"] = (timezone.now() - timedelta(seconds=120)).isoformat()
        round_obj.save(update_fields=["step_started_at"])

        response = self.client.get(reverse("survey:chat"))
        content = response.content.decode("utf-8")

        match = re.search(r'data-remaining-seconds="(\d+)"', content)
        self.assertIsNotNone(match)
        remaining = int(match.group(1))
        self.assertLess(remaining, 300)
        self.assertGreater(remaining, 150)

    def test_chat_script_reveals_stream_at_readable_pace(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "chat.js").read_text(encoding="utf-8")

        self.assertIn("function createTextRevealer", script)
        self.assertIn("window.setInterval(revealNext", script)
        self.assertIn("正在整理回复", script)
        self.assertIn("event: error", script)

    def test_chat_script_renders_markdown_without_raw_html(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "chat.js").read_text(encoding="utf-8")

        self.assertIn("function renderMarkdown", script)
        self.assertIn("function escapeHtml", script)
        self.assertIn("node.innerHTML = renderMarkdown", script)
        self.assertIn("data-markdown-source", script)

    def test_done_page_renders_completion_card_without_answers(self):
        user, batch = self.create_ready_user(username="p_done")
        SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_DONE,
            batch_snapshot={},
            topic_order_snapshot=[],
            submitted_topic_order=[1, 2, 3],
        )
        self.client.force_login(user)

        response = self.client.get(reverse("survey:done"))

        self.assertContains(response, "已完成，感谢你的参与")
        self.assertContains(response, "你的每一次选择和回答都很重要")
        self.assertContains(response, "完成徽章")
        self.assertNotContains(response, "submitted_topic_order")

    def test_reaction_script_toggles_same_choice_back_to_none(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "reactions.js").read_text(encoding="utf-8")

        self.assertIn('currentValue === button.dataset.reaction ? "none" : button.dataset.reaction', script)
        self.assertIn('button.setAttribute("aria-pressed", selected ? "true" : "false")', script)

    def test_quality_script_blocks_page_copy_paste_without_warning(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "quality-events.js").read_text(encoding="utf-8")

        self.assertIn('["paste", "drop", "copy", "cut"]', script)
        self.assertIn("blockPageTransfer", script)
        self.assertNotIn("function showWarning", script)
        self.assertNotIn("请直接输入你的想法，不要复制粘贴。", script)
        self.assertNotIn("data-no-paste-warning", script)

    def test_quality_script_blocks_browser_back_shortcuts_outside_editors(self):
        script = (Path(settings.BASE_DIR) / "static" / "survey" / "js" / "quality-events.js").read_text(encoding="utf-8")

        self.assertIn("function isEditableTarget", script)
        self.assertIn('event.key === "Backspace"', script)
        self.assertIn('event.key === "ArrowLeft" && event.altKey', script)
        self.assertIn('event.key === "BrowserBack"', script)
        self.assertIn("event.preventDefault()", script)
