from django.db import migrations, models


TRANSCRIBE_MODELS = {"whisper-1", "whisper-large", "whisper-large-v3"}


def classify_existing(apps, schema_editor):
    LLMProvider = apps.get_model("experiments", "LLMProvider")
    for provider in LLMProvider.objects.all().prefetch_related("api_keys"):
        is_transcribe = False
        for key in provider.api_keys.all():
            normalized = (key.model_name or "").replace("，", ",").replace("；", ";").replace("\r\n", "\n")
            tokens = []
            for line in normalized.replace(";", "\n").replace(",", "\n").split("\n"):
                value = line.strip()
                if value:
                    tokens.append(value)
            if any(t in TRANSCRIBE_MODELS for t in tokens):
                is_transcribe = True
                break
        if not is_transcribe and (provider.model_name or "") in TRANSCRIBE_MODELS:
            is_transcribe = True
        provider.kind = "transcribe" if is_transcribe else "chat"
        provider.save(update_fields=["kind"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0019_englishpaperconfig_gate_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmprovider",
            name="kind",
            field=models.CharField(
                choices=[("chat", "大模型"), ("transcribe", "语音转写")],
                default="chat",
                help_text="大模型用于 AI 对话，语音转写用于把录音转成文字。",
                max_length=20,
                verbose_name="用途",
            ),
        ),
        migrations.RunPython(classify_existing, reverse_noop),
    ]
