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
    region = forms.ChoiceField(
        label="地区",
        choices=[
            ("", "请选择地区"),
            ("中国大陆", "中国大陆"),
            ("港澳台", "港澳台"),
            ("海外", "海外"),
            ("其他", "其他"),
        ],
        required=False,
    )
    age_range = forms.ChoiceField(
        label="年龄段",
        choices=[
            ("", "请选择年龄段"),
            ("18岁以下", "18岁以下"),
            ("18-24岁", "18-24岁"),
            ("25-34岁", "25-34岁"),
            ("35-44岁", "35-44岁"),
            ("45岁及以上", "45岁及以上"),
        ],
        required=False,
    )
    gender = forms.ChoiceField(
        label="性别",
        choices=[
            ("", "请选择性别"),
            ("女", "女"),
            ("男", "男"),
            ("非二元/其他", "非二元/其他"),
            ("不方便透露", "不方便透露"),
        ],
        required=False,
    )
    organization_type = forms.ChoiceField(
        label="学校/单位类型",
        choices=[
            ("", "请选择类型"),
            ("初中", "初中"),
            ("高中", "高中"),
            ("大学/学院", "大学/学院"),
            ("企事业单位", "企事业单位"),
            ("其他", "其他"),
        ],
        required=False,
    )
    education_or_work = forms.ChoiceField(
        label="教育阶段/职业状态",
        choices=[
            ("", "请选择状态"),
            ("在校学生", "在校学生"),
            ("教师/教育工作者", "教师/教育工作者"),
            ("在职", "在职"),
            ("自由职业", "自由职业"),
            ("其他", "其他"),
        ],
        required=False,
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].required = True
        self.fields["display_name"].label = "称呼/姓名"
        self.fields["display_name"].help_text = "必填。可以填写昵称、称呼或姓名。"
        self.fields["display_name"].widget.attrs.update({"placeholder": "例如：小林"})
        self.fields["contact"].label = "联系方式"
        self.fields["contact"].required = False
        self.fields["contact"].widget.attrs.update({"placeholder": "选填，便于后续联系"})
        self.fields["notes"].label = "备注"
        self.fields["notes"].required = False
        self.fields["notes"].widget.attrs.update({"placeholder": "选填，可以补充任何你想说明的信息", "rows": 5})


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
