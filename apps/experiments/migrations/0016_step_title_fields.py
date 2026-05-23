from django.db import migrations, models


STEP_TITLES = [
    ("consent", "参与研究授权同意书", "Research Consent"),
    ("topic_order", "先排一排你最在意的话题", "Rank the topics you care about"),
    ("post", "阅读帖子与评论", "Read the post and comments"),
    ("emotion", "当前感受", "Current feeling"),
    ("stance_before", "你的观点", "Your view"),
    ("initial_text", "写下你的想法", "Write down your thoughts"),
    ("mode", "选择对话模式", "Choose conversation mode"),
    ("chat", "与人工智能对话", "Chat with the AI"),
    ("ai_eval", "对人工智能的评价", "Evaluate the AI"),
    ("stance_after", "再次确认你的观点", "Confirm your view again"),
    ("final_text", "写下你的新想法", "Write down your new thoughts"),
    ("english_paper", "英文论文写作", "English paper writing"),
    ("done", "已完成，感谢你的参与", "Completed. Thank you for your participation."),
]


def _build_operations():
    ops = []
    for step, zh_default, en_default in STEP_TITLES:
        ops.append(
            migrations.AddField(
                model_name="experimentbatch",
                name=f"step_title_{step}_zh",
                field=models.TextField(blank=True, default=zh_default, verbose_name=f"步骤标题：{step}（中文）"),
            )
        )
        ops.append(
            migrations.AddField(
                model_name="experimentbatch",
                name=f"step_title_{step}_en",
                field=models.TextField(blank=True, default=en_default, verbose_name=f"步骤标题：{step}（英文）"),
            )
        )
    return ops


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0015_consent_body_merge"),
    ]

    operations = _build_operations()
