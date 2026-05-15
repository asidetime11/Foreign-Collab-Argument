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
