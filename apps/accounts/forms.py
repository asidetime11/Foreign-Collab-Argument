from django import forms
from django.contrib.auth.models import User

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
