from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ParticipantProfile
from apps.experiments.models import ExperimentBatch


class ParticipantProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="p001", password="pass")

        profile = ParticipantProfile.objects.get(user=user)

        self.assertEqual(profile.display_name, "")
        self.assertFalse(profile.has_required_display_name)

    def test_raw_participant_profiles_are_hidden_from_admin(self):
        self.assertNotIn(ParticipantProfile, admin.site._registry)

    def test_registration_page_is_linked_from_login(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, reverse("accounts:register"))

    def test_registration_page_uses_chinese_account_copy(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertContains(response, "用户名")
        self.assertContains(response, "密码")
        self.assertContains(response, "确认密码")
        self.assertContains(response, "密码至少需要 5 位。")
        self.assertContains(response, 'class="form-field"')
        for text in ["Username", "Password", "Required", "confirmation", "English"]:
            self.assertNotContains(response, text)

    def test_registration_page_does_not_show_username_requirements(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertNotContains(response, "必填；长度不超过 150 个字符")
        self.assertNotContains(response, "可使用字母、数字和 @ . + - _")

    def test_registration_password_requires_at_least_five_characters(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "short_password",
                "password1": "1234",
                "password2": "1234",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "密码至少需要 5 位。")
        self.assertFalse(User.objects.filter(username="short_password").exists())

    def test_registration_errors_use_friendly_error_cards(self):
        User.objects.create_user("taken_name", password="pass123")

        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "taken_name",
                "password1": "12345",
                "password2": "54321",
            },
        )

        self.assertContains(response, 'class="form-errors"')
        self.assertContains(response, 'class="form-field has-error"')
        self.assertContains(response, "该用户名已存在。")
        self.assertContains(response, "两次输入的密码不一致。")

    def test_login_page_uses_chinese_account_copy(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "用户名")
        self.assertContains(response, "密码")
        self.assertContains(response, 'class="form-field"')
        for text in ["Username", "Password", "English"]:
            self.assertNotContains(response, text)

    def test_login_errors_use_friendly_error_cards(self):
        response = self.client.post(reverse("login"), {"username": "missing", "password": "wrong"})

        self.assertContains(response, 'class="form-errors form-errors-global"')
        self.assertContains(response, "用户名或密码不正确，请重新输入。")
        self.assertNotContains(response, "__all__")

    def test_authenticated_top_actions_use_account_menu(self):
        user = User.objects.create_user("p_nav", password="pass")
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:profile_edit"))

        self.assertContains(response, 'class="account-menu"')
        self.assertContains(response, 'class="account-link"')
        self.assertContains(response, 'class="account-logout"')

    def test_participant_can_register_and_get_default_batch(self):
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)

        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "new_participant",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )

        user = User.objects.get(username="new_participant")
        self.assertRedirects(response, reverse("accounts:profile_prompt"))
        self.assertEqual(user.participant_profile.batch, batch)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
