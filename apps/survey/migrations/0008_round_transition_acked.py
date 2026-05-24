from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("survey", "0007_duration_minutes"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveysession",
            name="round_transition_acked",
            field=models.BooleanField(default=True, verbose_name="已确认过渡提示"),
        ),
    ]
