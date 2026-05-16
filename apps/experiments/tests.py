from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from io import BytesIO
from openpyxl import load_workbook

from apps.survey.models import CommentReaction, ConversationMessage, ScaleResponse, SurveySession, TextResponse
from apps.accounts.models import ParticipantProfile

from .models import AIMode, ExperimentBatch, RatingScaleConfig, ScaleItem, Topic, TopicComment


class ExperimentModelTests(TestCase):
    def test_batch_defaults_match_design(self):
        batch = ExperimentBatch.objects.create(name="批次 A")

        self.assertEqual(batch.ai_chat_minutes, 5)
        self.assertEqual(batch.ai_neutrality, ExperimentBatch.NEUTRALITY_MODERATE)
        self.assertEqual(batch.topic_selection_strategy, ExperimentBatch.TOPIC_STRATEGY_HIGHEST_LOWEST)
        self.assertEqual(batch.round_order_strategy, ExperimentBatch.ROUND_RANDOM)

    def test_comment_presentation_is_generated(self):
        batch = ExperimentBatch.objects.create(name="批次 A")
        topic = Topic.objects.create(batch=batch, title_zh="话题", position=1)

        comment = TopicComment.objects.create(topic=topic, body_zh="这是评论", position=1)

        self.assertEqual(comment.auto_author_name, "")
        self.assertTrue(comment.avatar_seed)
        self.assertTrue(comment.relative_time)

    def test_seed_defaults_is_idempotent(self):
        call_command("seed_defaults")
        call_command("seed_defaults")

        batch = ExperimentBatch.objects.get(name__contains="Demo Batch")
        self.assertIn("我们正在进行一项关于中国青少年的研究", batch.intro_zh)
        self.assertEqual(Topic.objects.filter(batch=batch).count(), 10)
        self.assertEqual(AIMode.objects.filter(batch=batch).count(), 3)
        self.assertEqual(ScaleItem.objects.filter(batch=batch).count(), 4)

    def test_research_console_is_staff_only_and_links_editable_content(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        Topic.objects.create(batch=batch, title_zh="话题 A", position=1)
        AIMode.objects.create(batch=batch, name_zh="整理信息", prompt_zh="请整理信息。")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_dashboard"))

        self.assertContains(response, "研究管理台")
        self.assertContains(response, "第一步说明文字")
        self.assertContains(response, "话题材料")
        self.assertContains(response, "AI 模式 Prompt")
        self.assertContains(response, "一键导出全部用户数据")
        self.assertContains(response, reverse("research_admin_copy"))
        self.assertNotContains(response, reverse("research_admin_bulk_register"))
        self.assertContains(response, reverse("research_admin_export_all"))

    def test_admin_index_redirects_to_research_console(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ExperimentBatch.objects.create(name="批次 A")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, reverse("research_admin_dashboard"))

    def test_copy_settings_uses_custom_form_without_repeated_title(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ExperimentBatch.objects.create(name="批次 A", intro_zh="请按真实想法排序。")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_copy"))

        self.assertContains(response, "<h1>编辑第一步说明</h1>", html=True)
        self.assertContains(response, "说明内容")
        self.assertNotContains(response, "<h1>第一步说明文字</h1>", html=True)
        self.assertNotContains(response, "<p><label", html=False)

    def test_topic_and_ai_mode_admin_hide_batch_concept(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        Topic.objects.create(batch=batch, title_zh="话题 A", position=1)
        AIMode.objects.create(batch=batch, name_zh="整理信息", prompt_zh="请整理信息。")
        self.client.force_login(admin_user)

        topic_list = self.client.get(reverse("admin:experiments_topic_changelist"))
        topic_add = self.client.get(reverse("admin:experiments_topic_add"))
        ai_mode_list = self.client.get(reverse("admin:experiments_aimode_changelist"))
        ai_mode_add = self.client.get(reverse("admin:experiments_aimode_add"))

        for response in [topic_list, topic_add, ai_mode_list, ai_mode_add]:
            self.assertNotContains(response, "批次")
            self.assertNotContains(response, "batch")

    def test_model_admin_pages_link_back_to_research_console(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="Batch A")
        topic = Topic.objects.create(batch=batch, title_zh="Topic A", position=1)
        mode = AIMode.objects.create(batch=batch, name_zh="Mode A", prompt_zh="Prompt A")
        self.client.force_login(admin_user)

        responses = [
            self.client.get(reverse("admin:experiments_topic_changelist")),
            self.client.get(reverse("admin:experiments_topic_change", args=[topic.pk])),
            self.client.get(reverse("admin:experiments_aimode_changelist")),
            self.client.get(reverse("admin:experiments_aimode_change", args=[mode.pk])),
        ]

        for response in responses:
            self.assertContains(response, f'href="{reverse("research_admin_dashboard")}"')

    def test_topic_comment_inline_hides_generated_identity_fields(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A")
        topic = Topic.objects.create(batch=batch, title_zh="话题 A", position=1)
        TopicComment.objects.create(
            topic=topic,
            body_zh="评论 A",
            auto_author_name="周明",
            like_count=20,
            relative_time="刚刚",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:experiments_topic_change", args=[topic.pk]))

        self.assertContains(response, 'name="comments-0-like_count"')
        self.assertContains(response, 'name="comments-0-relative_time"')
        self.assertNotContains(response, "作者昵称")
        self.assertNotContains(response, 'name="comments-0-auto_author_name"')
        self.assertNotContains(response, "头像种子")
        self.assertNotContains(response, "avatar_seed")

    def test_bulk_register_export_downloads_excel_without_creating_users(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ExperimentBatch.objects.create(name="批次 A", is_active=True)
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("research_admin_bulk_register"),
            {
                "initial_password": "Start12345",
                "usernames": "student001\nstudent002",
                "action": "export",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        workbook = load_workbook(BytesIO(response.content))
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("用户名", "初始密码", "登录地址", "生成时间"))
        self.assertEqual(rows[1][0], "student001")
        self.assertEqual(rows[1][1], "Start12345")
        self.assertEqual(rows[2][0], "student002")
        self.assertFalse(User.objects.filter(username="student001").exists())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_export_all_includes_comment_reactions_sheet(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        participant = User.objects.create_user("p_react", password="Start12345")
        participant.participant_profile.display_name = "参与者"
        participant.participant_profile.batch = batch
        participant.participant_profile.save(update_fields=["display_name", "batch"])
        session = SurveySession.objects.create(
            user=participant,
            batch=batch,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        round_obj = session.rounds.create(
            round_type="high",
            topic_id=11,
            material_snapshot={
                "comments": [
                    {
                        "id": 101,
                        "author": "周明",
                        "body_zh": "这个观点很有意思。",
                        "relative_time": "刚刚",
                        "like_count": 20,
                    }
                ]
            },
        )
        CommentReaction.objects.create(round=round_obj, comment_snapshot_id=101, reaction="like")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_export_all"))

        workbook = load_workbook(BytesIO(response.content))
        self.assertIn("评论互动", workbook.sheetnames)
        sheet = workbook["评论互动"]
        rows = list(sheet.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("用户名", "轮次", "话题ID", "评论ID", "评论作者", "评论内容", "互动", "提交时间"))
        self.assertEqual(rows[1][0], "p_react")
        self.assertEqual(rows[1][3], 101)
        self.assertEqual(rows[1][4], "小兔")
        self.assertEqual(rows[1][5], "这个观点很有意思。")
        self.assertEqual(rows[1][6], "赞")

    def test_bulk_register_confirm_creates_users_then_shows_them_in_user_data(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("research_admin_bulk_register"),
            {
                "initial_password": "Start12345",
                "usernames": "student001\nstudent002",
                "action": "create",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("research_admin_users"))
        self.assertEqual(User.objects.get(username="student001").participant_profile.batch, batch)
        self.assertEqual(User.objects.get(username="student002").participant_profile.batch, batch)
        self.assertContains(response, "student001")
        self.assertContains(response, "student002")
        self.assertContains(response, "未开始")

    def test_bulk_register_page_uses_custom_design_without_batch_field(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ExperimentBatch.objects.create(name="批次 A", is_active=True)
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_bulk_register"))

        self.assertContains(response, "批量注册新用户")
        self.assertContains(response, "导出账号 Excel")
        self.assertContains(response, "确认创建账号")
        self.assertContains(response, "用户名列表")
        self.assertNotContains(response, "实验批次")
        self.assertNotContains(response, 'name="batch"')

    def test_bulk_register_page_can_generate_random_usernames(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        ExperimentBatch.objects.create(name="批次 A", is_active=True)
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_bulk_register"))

        self.assertContains(response, "随机生成用户名")
        self.assertContains(response, 'id="random-count"')
        self.assertContains(response, 'data-target="id_usernames"')
        self.assertContains(response, "adminGeneratedUsernames")
        self.assertContains(response, "随机生成 10 个用户名")

    def test_user_data_page_lists_registered_users_before_they_start(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        participant = User.objects.create_user("fresh_user", password="Start12345")
        participant.participant_profile.batch = batch
        participant.participant_profile.save(update_fields=["batch"])
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_users"))

        self.assertContains(response, "账号状态")
        self.assertContains(response, "fresh_user")
        self.assertContains(response, "未开始")
        self.assertContains(response, reverse("research_admin_bulk_register"))

    def test_user_data_page_has_single_and_bulk_delete_controls(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        participant = User.objects.create_user("delete_ready", password="Start12345")
        participant.participant_profile.batch = batch
        participant.participant_profile.save(update_fields=["batch"])
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_users"))

        self.assertContains(response, "批量删除选中用户")
        self.assertContains(response, 'name="user_ids"')
        self.assertContains(response, reverse("research_admin_delete_user", args=[participant.pk]))
        self.assertContains(response, "删除")

    def test_single_delete_user_removes_participant_account(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        participant = User.objects.create_user("delete_one", password="Start12345")
        participant.participant_profile.batch = batch
        participant.participant_profile.save(update_fields=["batch"])
        self.client.force_login(admin_user)

        response = self.client.post(reverse("research_admin_delete_user", args=[participant.pk]), follow=True)

        self.assertRedirects(response, reverse("research_admin_users"))
        self.assertFalse(User.objects.filter(username="delete_one").exists())
        self.assertContains(response, "已删除 1 个参与者账号")

    def test_bulk_delete_users_removes_selected_participant_accounts(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        first = User.objects.create_user("delete_a", password="Start12345")
        second = User.objects.create_user("delete_b", password="Start12345")
        keep = User.objects.create_user("keep_user", password="Start12345")
        for user in [first, second, keep]:
            user.participant_profile.batch = batch
            user.participant_profile.save(update_fields=["batch"])
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("research_admin_delete_users"),
            {"user_ids": [str(first.pk), str(second.pk)]},
            follow=True,
        )

        self.assertRedirects(response, reverse("research_admin_users"))
        self.assertFalse(User.objects.filter(username="delete_a").exists())
        self.assertFalse(User.objects.filter(username="delete_b").exists())
        self.assertTrue(User.objects.filter(username="keep_user").exists())
        self.assertContains(response, "已删除 2 个参与者账号")

    def test_delete_user_does_not_remove_staff_account(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        staff = User.objects.create_user("staff_in_batch", password="Start12345", is_staff=True)
        staff.participant_profile.batch = batch
        staff.participant_profile.save(update_fields=["batch"])
        self.client.force_login(admin_user)

        response = self.client.post(reverse("research_admin_delete_user", args=[staff.pk]), follow=True)

        self.assertTrue(User.objects.filter(username="staff_in_batch").exists())
        self.assertContains(response, "没有可删除的参与者账号")

    def test_raw_models_are_hidden_from_admin_registry(self):
        for model in [
            ExperimentBatch,
            ScaleItem,
            RatingScaleConfig,
            SurveySession,
            ScaleResponse,
            TextResponse,
            ConversationMessage,
            ParticipantProfile,
            User,
            Group,
        ]:
            self.assertNotIn(model, admin.site._registry)

        self.assertIn(Topic, admin.site._registry)
        self.assertIn(AIMode, admin.site._registry)
