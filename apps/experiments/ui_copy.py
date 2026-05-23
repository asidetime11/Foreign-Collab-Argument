"""UI copy fields exposed in the admin "界面文案" editor.

Each entry: (field_base_name, zh_label, zh_default, en_default, step_key, hint).

step_key 必须和 apps/survey/views.py 里的 STEP_META key 对应，用于 iframe 预览定位页面。
hint 给 admin 表单展示，告诉编辑者这段文字出现在哪。
"""

UI_COPY_FIELDS = [
    # consent
    (
        "consent_title",
        "同意书标题",
        "参与研究授权同意书",
        "Research Participation Consent",
        "consent",
        "同意书页面的大标题。",
    ),
    (
        "consent_body",
        "同意书正文",
        "欢迎参与本研究。本平台会记录你在任务中的排序、文字回答、量表选择、与 AI 的对话内容以及英文论文，用于后续学术研究分析。\n你的回答仅用于研究目的，数据会尽量以匿名方式整理。参与过程中请按照自己的真实想法作答；如果遇到不适或不想继续，可以停止参与并联系研究人员。\n点击同意表示你已了解本研究的基本内容，并自愿继续完成后续任务。",
        "Welcome. This platform records your rankings, text answers, scale selections, AI conversation content, and English paper for research analysis.\nYour answers are used for research only and will be anonymized where possible. Please answer truthfully. You may stop at any time and contact the research team.\nClicking agree means you understand the study and voluntarily continue.",
        "consent",
        "同意书正文（多段用回车分隔）。",
    ),
    (
        "consent_agree_label",
        "同意书勾选框文字",
        "我已阅读并同意以上内容",
        "I have read and agree to the above.",
        "consent",
        "勾选框旁的文字。",
    ),
    (
        "consent_submit_label",
        "同意书继续按钮",
        "同意并继续",
        "Agree and continue",
        "consent",
        "页面底部按钮文字。",
    ),
    # topic_order
    (
        "topic_order_direction",
        "排序方向提示",
        "从上到下：最重要 → 最不重要",
        "Top to bottom: most important → least important",
        "topic_order",
        "排序页顶部的方向说明。",
    ),
    (
        "topic_order_drag_tip",
        "排序操作提示",
        "拖动卡片可调整排序；拖到页面边缘会自动滚动，也可以用右侧按钮微调。",
        "Drag cards to reorder; the page auto-scrolls near edges, or use the buttons on the right.",
        "topic_order",
        "拖拽操作的提示文字。",
    ),
    (
        "topic_order_submit_warning",
        "排序提交警告",
        "提交后将进入下一站，排序不能返回修改。",
        "After submitting, you cannot return to change the order.",
        "topic_order",
        "提交按钮上方的红字提醒。",
    ),
    (
        "topic_order_submit_label",
        "排序提交按钮",
        "提交排序",
        "Submit ranking",
        "topic_order",
        "提交按钮文字。",
    ),
    # post
    (
        "post_intro",
        "阅读帖子提示",
        "读完帖子和留言后，可以给帖子和留言点赞或点踩~",
        "After reading the post and comments, you may like or dislike them.",
        "post",
        "阅读帖子页顶部的说明。",
    ),
    (
        "post_optional_hint",
        "评论互动可选提示",
        "评论互动不是必选项，读完即可继续。",
        "Reacting to comments is optional. Continue once you've read them.",
        "post",
        "继续按钮上方的提示。",
    ),
    (
        "post_continue_label",
        "阅读页继续按钮",
        "继续",
        "Continue",
        "post",
        "继续按钮文字。",
    ),
    # scale - emotion
    (
        "emotion_intro",
        "情绪量表说明",
        "像调音台一样标出你现在的感受。每一项都需要选择。",
        "Mark how you feel right now, like adjusting a mixer. Every item is required.",
        "emotion",
        "情绪量表页顶部说明。",
    ),
    (
        "emotion_legend_1",
        "情绪刻度 1",
        "完全没有",
        "Not at all",
        "emotion",
        "情绪量表底部 1 档说明。",
    ),
    (
        "emotion_legend_2",
        "情绪刻度 2",
        "少许",
        "A little",
        "emotion",
        "情绪量表底部 2 档说明。",
    ),
    (
        "emotion_legend_3",
        "情绪刻度 3",
        "适中",
        "Moderate",
        "emotion",
        "情绪量表底部 3 档说明。",
    ),
    (
        "emotion_legend_4",
        "情绪刻度 4",
        "强",
        "Strong",
        "emotion",
        "情绪量表底部 4 档说明。",
    ),
    (
        "emotion_legend_5",
        "情绪刻度 5",
        "非常强",
        "Very strong",
        "emotion",
        "情绪量表底部 5 档说明。",
    ),
    # scale - ai eval
    (
        "ai_eval_intro",
        "AI 评价量表说明",
        "给刚才的对话伙伴打几个标签。每一项都需要选择。",
        "Tag the partner you just talked with. Every item is required.",
        "ai_eval",
        "AI 评价量表页说明。",
    ),
    # scale - stance after
    (
        "stance_after_intro",
        "再次确认观点说明",
        "前面的回答已收起，请根据现在的想法重新选择。",
        "Your previous answers are hidden. Choose again based on your current view.",
        "stance_after",
        "再次确认你的观点页面说明。",
    ),
    # text
    (
        "text_initial_hint",
        "AI 对话前文字提示",
        "把你现在想到的写下来就好，不需要标准答案。",
        "Write down what you're thinking now. There's no correct answer.",
        "initial_text",
        "AI 对话前写想法页的提示。",
    ),
    (
        "text_final_hint",
        "AI 对话后文字提示",
        "请再次写下你现在的想法，可以和之前相同，也可以不同。",
        "Write down your current thoughts again. They can match or differ from before.",
        "final_text",
        "AI 对话后写新想法页的提示。",
    ),
    # mode
    (
        "mode_intro",
        "AI 模式选择说明",
        "接下来可以选择一种方式和人工智能聊一聊，也可以跳过。",
        "Now choose how you'd like to chat with the AI, or skip.",
        "mode",
        "选择对话模式页说明。",
    ),
    # chat
    (
        "chat_input_placeholder",
        "聊天输入框 placeholder",
        "直接输入你想聊的内容",
        "Type what you want to discuss",
        "chat",
        "聊天框里的灰色提示文字。",
    ),
    (
        "chat_send_label",
        "发送按钮文字",
        "发送",
        "Send",
        "chat",
        "聊天发送按钮文字。",
    ),
    (
        "chat_finish_modal_title",
        "结束对话确认标题",
        "确认完成这轮对话吗？",
        "Finish this round of conversation?",
        "chat",
        "结束对话的弹窗标题。",
    ),
    (
        "chat_finish_modal_body",
        "结束对话确认正文",
        "提交后将进入下一步，不能继续本轮 AI 对话。",
        "After submitting, you'll move to the next step and cannot continue this round.",
        "chat",
        "结束对话弹窗的提示。",
    ),
    # done
    (
        "done_title",
        "完成页标题",
        "已完成，感谢你的参与",
        "Completed. Thank you for your participation.",
        "done",
        "结束页大标题。",
    ),
    (
        "done_body",
        "完成页正文",
        "你的每一次选择和回答都很重要。感谢你认真完成这次研究任务。",
        "Every answer matters. Thank you for completing this study.",
        "done",
        "结束页正文。",
    ),
    # ── Step titles (顶部 H1，也用于 admin 下拉与浏览器标签) ──
    ("step_title_consent", "步骤标题：同意书", "参与研究授权同意书", "Research Consent", "consent", "页面顶部的 H1。"),
    ("step_title_topic_order", "步骤标题：话题排序", "先排一排你最在意的话题", "Rank the topics you care about", "topic_order", "页面顶部的 H1。"),
    ("step_title_post", "步骤标题：阅读帖子", "阅读帖子与评论", "Read the post and comments", "post", "页面顶部的 H1。"),
    ("step_title_emotion", "步骤标题：当前感受", "当前感受", "Current feeling", "emotion", "页面顶部的 H1。"),
    ("step_title_stance_before", "步骤标题：你的观点", "你的观点", "Your view", "stance_before", "页面顶部的 H1。"),
    ("step_title_initial_text", "步骤标题：写下你的想法", "写下你的想法", "Write down your thoughts", "initial_text", "页面顶部的 H1。"),
    ("step_title_mode", "步骤标题：选择对话模式", "选择对话模式", "Choose conversation mode", "mode", "页面顶部的 H1。"),
    ("step_title_chat", "步骤标题：AI 对话", "与人工智能对话", "Chat with the AI", "chat", "页面顶部的 H1。"),
    ("step_title_ai_eval", "步骤标题：AI 评价", "对人工智能的评价", "Evaluate the AI", "ai_eval", "页面顶部的 H1。"),
    ("step_title_stance_after", "步骤标题：再次确认你的观点", "再次确认你的观点", "Confirm your view again", "stance_after", "页面顶部的 H1。"),
    ("step_title_final_text", "步骤标题：写下你的新想法", "写下你的新想法", "Write down your new thoughts", "final_text", "页面顶部的 H1。"),
    ("step_title_english_paper", "步骤标题：英文论文", "英文论文写作", "English paper writing", "english_paper", "页面顶部的 H1。"),
    ("step_title_done", "步骤标题：完成", "已完成，感谢你的参与", "Completed. Thank you for your participation.", "done", "页面顶部的 H1。"),
]


def field_names_zh_en():
    """Return list of (zh_field, en_field) for migrations / forms."""
    return [(f"{base}_zh", f"{base}_en") for base, *_ in UI_COPY_FIELDS]


def group_fields_by_step():
    """Return dict step_key -> list of (base, zh_label, zh_default, en_default, hint)."""
    groups = {}
    for base, zh_label, zh_default, en_default, step, hint in UI_COPY_FIELDS:
        groups.setdefault(step, []).append((base, zh_label, zh_default, en_default, hint))
    return groups
