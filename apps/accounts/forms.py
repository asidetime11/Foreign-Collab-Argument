from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator

from .models import ParticipantProfile


class NicknameForm(forms.ModelForm):
    class Meta:
        model = ParticipantProfile
        fields = ["display_name"]


class ParticipantProfileForm(forms.ModelForm):
    class Meta:
        model = ParticipantProfile
        fields = [
            "display_name",
            "region",
            "age_range",
            "gender",
            "organization_type",
            "education_or_work",
            "contact",
            "notes",
        ]


class ParticipantRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "用户名"
        self.fields["username"].help_text = ""
        self.fields["username"].error_messages.update(
            {
                "required": "请输入用户名。",
                "unique": "该用户名已存在。",
                "invalid": "用户名只能包含字母、数字和 @ . + - _。",
            }
        )
        self.fields["password1"].label = "密码"
        self.fields["password1"].help_text = "密码至少需要 5 位。"
        self.fields["password1"].widget.attrs["minlength"] = 5
        self.fields["password1"].validators.append(
            MinLengthValidator(5, message="密码至少需要 5 位。")
        )
        self.fields["password1"].error_messages.update({"required": "请输入密码。"})
        self.fields["password2"].label = "确认密码"
        self.fields["password2"].help_text = "请再次输入相同密码。"
        self.fields["password2"].error_messages.update({"required": "请再次输入密码。"})

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("两次输入的密码不一致。")
        return password2


class ChineseAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="用户名")
    password = forms.CharField(label="密码", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    error_messages = {
        "invalid_login": "用户名或密码不正确，请重新输入。",
        "inactive": "该账号已停用。",
    }


class BulkParticipantCreateForm(forms.Form):
    batch = forms.ModelChoiceField(queryset=None, label="实验批次")
    initial_password = forms.CharField(label="初始密码", widget=forms.PasswordInput)
    usernames = forms.CharField(label="用户名", widget=forms.Textarea, help_text="每行一个用户名")

    def __init__(self, *args, **kwargs):
        from apps.experiments.models import ExperimentBatch

        super().__init__(*args, **kwargs)
        self.fields["batch"].queryset = ExperimentBatch.objects.all()

    def clean_usernames(self):
        raw = self.cleaned_data["usernames"]
        usernames = [line.strip() for line in raw.splitlines() if line.strip()]
        if not usernames:
            raise forms.ValidationError("请至少输入一个用户名。")
        duplicates = {name for name in usernames if usernames.count(name) > 1}
        if duplicates:
            raise forms.ValidationError(f"用户名重复：{', '.join(sorted(duplicates))}")
        existing = set(User.objects.filter(username__in=usernames).values_list("username", flat=True))
        if existing:
            raise forms.ValidationError(f"用户名已存在：{', '.join(sorted(existing))}")
        return usernames
