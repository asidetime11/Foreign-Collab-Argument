from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("survey", "0006_alter_surveysession_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="englishpaperresponse",
            name="duration_minutes",
            field=models.PositiveIntegerField(default=0, verbose_name="时长（分钟）"),
        ),
        migrations.AddField(
            model_name="englishpaperdraft",
            name="duration_minutes",
            field=models.PositiveIntegerField(default=0, verbose_name="时长（分钟）"),
        ),
    ]
