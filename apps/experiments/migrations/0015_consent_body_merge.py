from django.db import migrations, models


def merge_paragraphs(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    for batch in ExperimentBatch.objects.all():
        zh_parts = [
            (getattr(batch, "consent_paragraph_1_zh", "") or "").strip(),
            (getattr(batch, "consent_paragraph_2_zh", "") or "").strip(),
            (getattr(batch, "consent_paragraph_3_zh", "") or "").strip(),
        ]
        en_parts = [
            (getattr(batch, "consent_paragraph_1_en", "") or "").strip(),
            (getattr(batch, "consent_paragraph_2_en", "") or "").strip(),
            (getattr(batch, "consent_paragraph_3_en", "") or "").strip(),
        ]
        batch.consent_body_zh = "\n".join(p for p in zh_parts if p)
        batch.consent_body_en = "\n".join(p for p in en_parts if p)
        batch.save(update_fields=["consent_body_zh", "consent_body_en"])


def split_paragraphs(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    for batch in ExperimentBatch.objects.all():
        zh_parts = (batch.consent_body_zh or "").split("\n")
        en_parts = (batch.consent_body_en or "").split("\n")
        while len(zh_parts) < 3:
            zh_parts.append("")
        while len(en_parts) < 3:
            en_parts.append("")
        batch.consent_paragraph_1_zh = zh_parts[0]
        batch.consent_paragraph_2_zh = zh_parts[1]
        batch.consent_paragraph_3_zh = "\n".join(zh_parts[2:])
        batch.consent_paragraph_1_en = en_parts[0]
        batch.consent_paragraph_2_en = en_parts[1]
        batch.consent_paragraph_3_en = "\n".join(en_parts[2:])
        batch.save()


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0014_experimentbatch_ui_copy_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="experimentbatch",
            name="consent_body_zh",
            field=models.TextField(blank=True, default="", verbose_name="同意书正文（中文）"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="consent_body_en",
            field=models.TextField(blank=True, default="", verbose_name="同意书正文（英文）"),
        ),
        migrations.RunPython(merge_paragraphs, split_paragraphs),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_1_zh"),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_1_en"),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_2_zh"),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_2_en"),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_3_zh"),
        migrations.RemoveField(model_name="experimentbatch", name="consent_paragraph_3_en"),
    ]
