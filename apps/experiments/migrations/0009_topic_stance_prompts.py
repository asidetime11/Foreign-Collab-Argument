from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0008_topic_batches_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="topic",
            name="agreement_prompt_zh",
            field=models.TextField(
                blank=True,
                help_text='打分页面"你的观点/再次确认你的观点"中第一题的提问文字。可使用 {statement} 占位符插入上方的观点陈述。留空则使用默认文案。',
                verbose_name="同意度提问（中文）",
            ),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_prompt_en",
            field=models.TextField(
                blank=True,
                help_text="English version of the agreement prompt. You may use {statement} as a placeholder.",
                verbose_name="同意度提问（英文）",
            ),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_prompt_zh",
            field=models.TextField(
                blank=True,
                help_text="打分页面中第二题的提问文字。可使用 {statement} 占位符。留空则使用默认文案。",
                verbose_name="确定度提问（中文）",
            ),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_prompt_en",
            field=models.TextField(
                blank=True,
                help_text="English version of the confidence prompt. You may use {statement} as a placeholder.",
                verbose_name="确定度提问（英文）",
            ),
        ),
    ]
