DEFAULT_TOPIC_ORDER_INTRO_ZH = (
    "我们正在进行一项关于中国青少年的研究，希望了解高中生们对各种复杂问题的看法，十分需要你的帮助。"
    "我们不会评判你的回答的对错，你的回答也不会影响在校成绩。你的老师、家长和同学都不会看到你的实名回答，"
    "只有研究团队的成员会将你的回答用于研究用途。\n"
    "现在，请按照你的想法从（1）对你最重要 -- （10）对你最不重要，为下列话题进行排序。"
)

DEFAULT_TOPIC_ORDER_INTRO_EN = (
    "We are conducting a study about Chinese adolescents and would like to understand high school students' views "
    "on complex social questions. Your help is very important. We will not judge whether your answers are right or "
    "wrong, and your answers will not affect your school grades. Your teachers, parents, and classmates will not see "
    "your named responses; only the research team will use them for research purposes.\n"
    "Now, please rank the topics below from (1) most important to you to (10) least important to you."
)

DEFAULT_AI_MODES = [
    {
        "name_zh": "提出不同观点",
        "name_en": "Offer a different view",
        "prompt_zh": "请基于参与者当前观点，温和地提出一个不同角度或可能的反例，帮助参与者思考问题的复杂性。不要攻击参与者，不要强行说服，不要给出绝对结论。回复应简洁、自然，并以一个开放式问题结束。",
        "prompt_en": "Gently offer a different angle or possible counterexample based on the participant's current view. Do not attack, force persuasion, or state absolute conclusions. Keep the reply concise and natural, ending with an open question.",
    },
    {
        "name_zh": "支持我的观点",
        "name_en": "Support my view",
        "prompt_zh": "请理解并复述参与者的主要观点，补充一到两个可能支持该观点的理由或背景。保持适度中立，不要夸大证据，不要暗示该观点一定正确。",
        "prompt_en": "Reflect the participant's main view and add one or two possible supporting reasons or background points. Stay moderately neutral and avoid overstating certainty.",
    },
    {
        "name_zh": "总结信息",
        "name_en": "Summarize information",
        "prompt_zh": "请把当前问题中可能相关的信息和不同解释路径整理清楚，帮助参与者看见问题的多个层面。不要替参与者下结论，不要要求参与者改变观点。",
        "prompt_en": "Organize relevant information and possible interpretations so the participant can see multiple layers of the issue. Do not decide for them or ask them to change their view.",
    },
]

DEFAULT_TOPICS = [
    ("大学课堂应更多使用 AI 工具", "University classes should use more AI tools"),
    ("远程办公会削弱团队合作", "Remote work weakens teamwork"),
    ("短视频平台应限制青少年使用时间", "Short-video platforms should limit teen usage time"),
    ("城市应优先发展公共交通", "Cities should prioritize public transit"),
    ("学校应减少标准化考试", "Schools should reduce standardized testing"),
    ("社交媒体让公共讨论更理性", "Social media makes public debate more rational"),
    ("企业应公开算法推荐规则", "Companies should disclose recommendation algorithms"),
    ("大学生应被鼓励创业", "University students should be encouraged to start businesses"),
    ("网络匿名有利于真实表达", "Online anonymity helps honest expression"),
    ("博物馆应免费开放", "Museums should be free to enter"),
]

DEFAULT_SCALE_ITEMS = [
    ("emotion", "我现在感到放松", "I feel relaxed right now"),
    ("emotion", "我现在感到被激发思考", "I feel intellectually engaged right now"),
    ("ai_eval", "AI 的回复有帮助", "The AI response was helpful"),
    ("ai_eval", "AI 的回复保持了中立", "The AI response remained neutral"),
]
