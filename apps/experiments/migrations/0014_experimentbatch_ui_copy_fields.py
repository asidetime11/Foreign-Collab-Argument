from django.db import migrations, models


# Snapshot of UI_COPY_FIELDS at the time of this migration.
# Static so future code changes to ui_copy.py don't break migration history.
INITIAL_FIELDS = [
    ("consent_title", "同意书标题", "参与研究授权同意书", "Research Participation Consent"),
    ("consent_paragraph_1", "同意书正文 1",
     "欢迎参与本研究。本平台会记录你在任务中的排序、文字回答、量表选择、与 AI 的对话内容以及英文论文，用于后续学术研究分析。",
     "Welcome. This platform records your rankings, text answers, scale selections, AI conversation content, and English paper for research analysis."),
    ("consent_paragraph_2", "同意书正文 2",
     "你的回答仅用于研究目的，数据会尽量以匿名方式整理。参与过程中请按照自己的真实想法作答；如果遇到不适或不想继续，可以停止参与并联系研究人员。",
     "Your answers are used for research only and will be anonymized where possible. Please answer truthfully. You may stop at any time and contact the research team."),
    ("consent_paragraph_3", "同意书正文 3",
     "点击同意表示你已了解本研究的基本内容，并自愿继续完成后续任务。",
     "Clicking agree means you understand the study and voluntarily continue."),
    ("consent_agree_label", "同意书勾选框文字", "我已阅读并同意以上内容", "I have read and agree to the above."),
    ("consent_submit_label", "同意书继续按钮", "同意并继续", "Agree and continue"),
    ("topic_order_direction", "排序方向提示", "从上到下：最重要 → 最不重要", "Top to bottom: most important → least important"),
    ("topic_order_drag_tip", "排序操作提示",
     "拖动卡片可调整排序；拖到页面边缘会自动滚动，也可以用右侧按钮微调。",
     "Drag cards to reorder; the page auto-scrolls near edges, or use the buttons on the right."),
    ("topic_order_submit_warning", "排序提交警告",
     "提交后将进入下一站，排序不能返回修改。",
     "After submitting, you cannot return to change the order."),
    ("topic_order_submit_label", "排序提交按钮", "提交排序", "Submit ranking"),
    ("post_intro", "阅读帖子提示",
     "读完帖子和留言后，可以给帖子和留言点赞或点踩~",
     "After reading the post and comments, you may like or dislike them."),
    ("post_optional_hint", "评论互动可选提示",
     "评论互动不是必选项，读完即可继续。",
     "Reacting to comments is optional. Continue once you've read them."),
    ("post_continue_label", "阅读页继续按钮", "继续", "Continue"),
    ("emotion_intro", "情绪量表说明",
     "像调音台一样标出你现在的感受。每一项都需要选择。",
     "Mark how you feel right now, like adjusting a mixer. Every item is required."),
    ("emotion_legend_1", "情绪刻度 1", "完全没有", "Not at all"),
    ("emotion_legend_2", "情绪刻度 2", "少许", "A little"),
    ("emotion_legend_3", "情绪刻度 3", "适中", "Moderate"),
    ("emotion_legend_4", "情绪刻度 4", "强", "Strong"),
    ("emotion_legend_5", "情绪刻度 5", "非常强", "Very strong"),
    ("ai_eval_intro", "AI 评价量表说明",
     "给刚才的对话伙伴打几个标签。每一项都需要选择。",
     "Tag the partner you just talked with. Every item is required."),
    ("stance_after_intro", "再次确认观点说明",
     "前面的回答已收起，请根据现在的想法重新选择。",
     "Your previous answers are hidden. Choose again based on your current view."),
    ("text_initial_hint", "AI 对话前文字提示",
     "把你现在想到的写下来就好，不需要标准答案。",
     "Write down what you're thinking now. There's no correct answer."),
    ("text_final_hint", "AI 对话后文字提示",
     "请再次写下你现在的想法，可以和之前相同，也可以不同。",
     "Write down your current thoughts again. They can match or differ from before."),
    ("mode_intro", "AI 模式选择说明",
     "接下来可以选择一种方式和人工智能聊一聊，也可以跳过。",
     "Now choose how you'd like to chat with the AI, or skip."),
    ("chat_input_placeholder", "聊天输入框 placeholder", "直接输入你想聊的内容", "Type what you want to discuss"),
    ("chat_send_label", "发送按钮文字", "发送", "Send"),
    ("chat_finish_modal_title", "结束对话确认标题", "确认完成这轮对话吗？", "Finish this round of conversation?"),
    ("chat_finish_modal_body", "结束对话确认正文",
     "提交后将进入下一步，不能继续本轮 AI 对话。",
     "After submitting, you'll move to the next step and cannot continue this round."),
    ("done_title", "完成页标题", "已完成，感谢你的参与", "Completed. Thank you for your participation."),
    ("done_body", "完成页正文",
     "你的每一次选择和回答都很重要。感谢你认真完成这次研究任务。",
     "Every answer matters. Thank you for completing this study."),
]


def _build_operations():
    ops = []
    for base, zh_label, zh_default, en_default in INITIAL_FIELDS:
        ops.append(
            migrations.AddField(
                model_name="experimentbatch",
                name=f"{base}_zh",
                field=models.TextField(blank=True, default=zh_default, verbose_name=f"{zh_label}（中文）"),
            )
        )
        ops.append(
            migrations.AddField(
                model_name="experimentbatch",
                name=f"{base}_en",
                field=models.TextField(blank=True, default=en_default, verbose_name=f"{zh_label}（英文）"),
            )
        )
    return ops


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0013_move_stance_labels_back_to_batch"),
    ]

    operations = _build_operations()
