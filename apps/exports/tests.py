import zipfile
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.experiments.models import ExperimentBatch
from apps.survey.models import ConversationMessage, QualityEvent, ScaleResponse, SurveySession, TextResponse, TopicRound

from .services import build_all_users_excel, build_csv_zip, build_excel


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
        QualityEvent.objects.create(user=user, session=session, event_type="copy")

    def test_excel_contains_selected_sheets(self):
        payload = build_excel(self.batch, ["participants", "scale_responses"])

        workbook = load_workbook(BytesIO(payload))

        self.assertIn("participants", workbook.sheetnames)
        self.assertIn("scale_responses", workbook.sheetnames)

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

        summary = workbook["用户总表"]
        headers = [cell.value for cell in summary[1]]
        row = [cell.value for cell in summary[2]]
        data = dict(zip(headers, row))

        self.assertEqual(data["用户名"], "p001")
        self.assertEqual(data["称呼/姓名"], "参与者")
        self.assertIn("放松=5", data["感受"])
        self.assertEqual(data["初始想法"], "想法")

        conversation = workbook["AI对话"]
        self.assertEqual(conversation["A2"].value, "p001")
        self.assertEqual(conversation["D2"].value, "你好")

    def test_research_admin_one_click_export_downloads_all_users_excel(self):
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("research_admin_export_all"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("all-users-research-data", response["Content-Disposition"])
