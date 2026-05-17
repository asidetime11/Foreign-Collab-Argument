import csv
import zipfile
from io import BytesIO, StringIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.experiments.models import ExperimentBatch
from apps.survey.models import ConversationMessage, EnglishPaperResponse, PostReaction, QualityEvent, ScaleResponse, SurveySession, TextResponse, TopicRound

from .services import build_all_users_csv, build_all_users_excel, build_csv_zip, build_excel


class ExportServiceTests(TestCase):
    def setUp(self):
        self.batch = ExperimentBatch.objects.create(name="批次 A")
        user = User.objects.create_user("p001", password="pass")
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = self.batch
        user.participant_profile.save()
        session = SurveySession.objects.create(user=user, batch=self.batch, topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(session=session, round_type=TopicRound.HIGH, topic_id=1)
        ScaleResponse.objects.create(round=round_obj, step="emotion", item_type="emotion", item_label="放松", language="zh-hans", selected_value=5)
        TextResponse.objects.create(round=round_obj, step="initial_text", final_text="想法", word_count=2)
        ConversationMessage.objects.create(round=round_obj, role="participant", content="你好", language="zh-hans")
        PostReaction.objects.create(round=round_obj, reaction="like")
        EnglishPaperResponse.objects.create(session=session, prompt="Write an essay.", duration_hours=24, paper_text="My English essay.")
        QualityEvent.objects.create(user=user, session=session, event_type="copy")

    def test_excel_contains_selected_sheets(self):
        payload = build_excel(self.batch, ["participants", "scale_responses"])

        workbook = load_workbook(BytesIO(payload))

        self.assertIn("participants", workbook.sheetnames)
        self.assertIn("scale_responses", workbook.sheetnames)

    def test_excel_can_export_post_reactions(self):
        payload = build_excel(self.batch, ["post_reactions"])

        workbook = load_workbook(BytesIO(payload))
        self.assertIn("post_reactions", workbook.sheetnames)
        sheet = workbook["post_reactions"]
        headers = [cell.value for cell in sheet[1]]
        row = [cell.value for cell in sheet[2]]
        data = dict(zip(headers, row))

        self.assertEqual(data["username"], "p001")
        self.assertEqual(data["reaction"], "like")

    def test_csv_zip_contains_selected_files(self):
        payload = build_csv_zip(self.batch, ["participants", "quality_events"])

        with zipfile.ZipFile(BytesIO(payload)) as archive:
            self.assertIn("participants.csv", archive.namelist())
            self.assertIn("quality_events.csv", archive.namelist())

    def test_all_users_excel_is_organized_by_user(self):
        payload = build_all_users_excel()

        workbook = load_workbook(BytesIO(payload))
        self.assertIn("用户总表", workbook.sheetnames)
        self.assertIn("AI对话", workbook.sheetnames)
        self.assertIn("帖子互动", workbook.sheetnames)

        summary = workbook["用户总表"]
        headers = [cell.value for cell in summary[1]]
        row = [cell.value for cell in summary[2]]
        data = dict(zip(headers, row))

        self.assertEqual(data["用户名"], "p001")
        self.assertEqual(data["称呼/姓名"], "参与者")
        self.assertIn("放松=5", data["感受"])
        self.assertEqual(data["初始想法"], "想法")
        self.assertEqual(data["英文论文"], "My English essay.")

        conversation = workbook["AI对话"]
        self.assertEqual(conversation["A2"].value, "p001")
        self.assertEqual(conversation["D2"].value, "你好")

        post_reactions = workbook["帖子互动"]
        self.assertEqual(post_reactions["A2"].value, "p001")

    def test_all_users_csv_is_organized_by_user(self):
        payload = build_all_users_csv()

        text = payload.decode("utf-8-sig")
        rows = list(csv.DictReader(StringIO(text)))

        self.assertEqual(rows[0]["用户名"], "p001")
        self.assertEqual(rows[0]["称呼/姓名"], "参与者")
        self.assertIn("放松=5", rows[0]["感受"])
        self.assertEqual(rows[0]["初始想法"], "想法")
        self.assertEqual(rows[0]["英文论文"], "My English essay.")
        self.assertIn("赞", rows[0]["帖子互动"])
        self.assertIn("你好", rows[0]["AI对话"])

    def test_research_admin_one_click_export_downloads_all_users_csv(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_export_all"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("all-users-research-data", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])
