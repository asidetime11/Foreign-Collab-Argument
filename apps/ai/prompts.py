from apps.experiments.models import ExperimentBatch


MODERATE_NEUTRALITY_ZH = "保持适度中立：可以提供背景、解释和反例，但避免强行下结论或诱导参与者改变观点。"
STRICT_NEUTRALITY_ZH = "保持严格中立：只澄清概念和信息结构，不提供倾向性建议，不评价观点优劣。"
MODERATE_NEUTRALITY_EN = "Stay moderately neutral: offer background, explanations, and counterexamples without forcing conclusions or nudging the participant to change views."
STRICT_NEUTRALITY_EN = "Stay strictly neutral: clarify concepts and information structure without directional advice or evaluation."


def build_system_prompt(batch, mode, language):
    is_en = language.startswith("en")
    if batch.ai_neutrality == ExperimentBatch.NEUTRALITY_STRICT:
        neutrality = STRICT_NEUTRALITY_EN if is_en else STRICT_NEUTRALITY_ZH
    else:
        neutrality = MODERATE_NEUTRALITY_EN if is_en else MODERATE_NEUTRALITY_ZH
    language_line = "Reply in English." if is_en else "请使用中文回复。"
    mode_prompt = mode.prompt_en if is_en and mode.prompt_en else mode.prompt_zh
    return "\n\n".join([neutrality, language_line, mode_prompt])


def build_intro_user_message(mode, material_snapshot, stance_scores, initial_text, language):
    """Build the user-side context message that triggers the AI intro at chat start.

    stance_scores: list of (item_label, selected_value, min_value, max_value) tuples from stance_before
    initial_text: str, participant's initial written thought (may be empty)
    """
    is_en = language.startswith("en")

    intro_template = (
        (mode.intro_template_en if is_en and mode.intro_template_en else mode.intro_template_zh)
        if (mode.intro_template_zh or mode.intro_template_en)
        else None
    )
    if not intro_template:
        return None

    if is_en:
        topic_title = material_snapshot.get("title_en") or material_snapshot.get("title_zh") or ""
        post_body = material_snapshot.get("post_body_en") or material_snapshot.get("post_body_zh") or ""
        statement = material_snapshot.get("statement_en") or material_snapshot.get("statement_zh") or ""
    else:
        topic_title = material_snapshot.get("title_zh") or material_snapshot.get("title_en") or ""
        post_body = material_snapshot.get("post_body_zh") or material_snapshot.get("post_body_en") or ""
        statement = material_snapshot.get("statement_zh") or material_snapshot.get("statement_en") or ""

    if is_en:
        lines = ["[User Background]"]
        lines.append(f"Topic: {topic_title}")
        if statement:
            lines.append(f"Statement: {statement}")
        if post_body:
            lines.append(f"Post: {post_body}")
        if stance_scores:
            score_parts = "; ".join(
                f"{label}: {val}/{max_val}" for label, val, _min, max_val in stance_scores
            )
            lines.append(f"Opinion scores (before chat): {score_parts}")
        if initial_text:
            lines.append(f"Initial thoughts: {initial_text}")
        lines.append("")
        lines.append("[Your Task]")
        lines.append(intro_template)
    else:
        lines = ["【用户背景信息】"]
        lines.append(f"话题：{topic_title}")
        if statement:
            lines.append(f"观点陈述：{statement}")
        if post_body:
            lines.append(f"帖子内容：{post_body}")
        if stance_scores:
            score_parts = "；".join(
                f"{label}：{val}/{max_val}" for label, val, _min, max_val in stance_scores
            )
            lines.append(f"观点打分（对话前）：{score_parts}")
        if initial_text:
            lines.append(f"用户的初始想法：{initial_text}")
        lines.append("")
        lines.append("【你的任务】")
        lines.append(intro_template)

    return "\n".join(lines)

