from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0018_englishpaperconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_title_zh",
            field=models.CharField(default="即将进入写作模块", max_length=200, verbose_name="入口页标题（中文）"),
        ),
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_title_en",
            field=models.CharField(default="You're About to Enter the Writing Module", max_length=200, verbose_name="入口页标题（英文）"),
        ),
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_body_zh",
            field=models.TextField(blank=True, default='接下来你将进行英文论文写作。请放轻松，根据你对话题的理解，用英文写一篇论证性短文。计时将在你点击"进入写作"后开始。', verbose_name="入口页说明（中文）"),
        ),
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_body_en",
            field=models.TextField(blank=True, default='You will now write a short argumentative essay in English. Take a deep breath and relax. The timer will start after you click "Start Writing".', verbose_name="入口页说明（英文）"),
        ),
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_cta_zh",
            field=models.CharField(default="进入写作", max_length=100, verbose_name="入口按钮文字（中文）"),
        ),
        migrations.AddField(
            model_name="englishpaperconfig",
            name="gate_cta_en",
            field=models.CharField(default="Start Writing", max_length=100, verbose_name="入口按钮文字（英文）"),
        ),
    ]
