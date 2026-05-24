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
        "intro_template_zh": (
            "请根据以下用户背景信息，用两到三句话向用户说明接下来的对话方式：你将温和地从不同角度与用户探讨这个话题，帮助他们看到问题的另一面，但不会强迫他们改变想法。语气友善自然，结尾可以简短邀请用户开始分享。"
        ),
        "intro_template_en": (
            "Based on the user background below, write two to three sentences to introduce how the conversation will work: "
            "you will gently explore different angles of the topic with the user to help them see another side, "
            "without pressuring them to change their mind. Keep the tone warm and natural, and briefly invite them to start sharing."
        ),
    },
    {
        "name_zh": "支持我的观点",
        "name_en": "Support my view",
        "prompt_zh": "请理解并复述参与者的主要观点，补充一到两个可能支持该观点的理由或背景。保持适度中立，不要夸大证据，不要暗示该观点一定正确。",
        "prompt_en": "Reflect the participant's main view and add one or two possible supporting reasons or background points. Stay moderately neutral and avoid overstating certainty.",
        "intro_template_zh": (
            "请根据以下用户背景信息，用两到三句话向用户说明接下来的对话方式：你将帮助用户整理和补充支持他们已有观点的理由和背景，让他们能更清晰地表达自己的立场。语气积极支持，结尾简短邀请用户开始分享。"
        ),
        "intro_template_en": (
            "Based on the user background below, write two to three sentences to introduce how the conversation will work: "
            "you will help the user organize and expand on the reasons and context that support their existing view, "
            "so they can express their stance more clearly. Keep the tone encouraging, and briefly invite them to start sharing."
        ),
    },
    {
        "name_zh": "总结信息",
        "name_en": "Summarize information",
        "prompt_zh": "请把当前问题中可能相关的信息和不同解释路径整理清楚，帮助参与者看见问题的多个层面。不要替参与者下结论，不要要求参与者改变观点。",
        "prompt_en": "Organize relevant information and possible interpretations so the participant can see multiple layers of the issue. Do not decide for them or ask them to change their view.",
        "intro_template_zh": (
            "请根据以下用户背景信息，用两到三句话向用户说明接下来的对话方式：你将帮助用户梳理围绕这个话题的不同信息和解读角度，让他们对问题的全貌有更清晰的认识，而不会替他们下结论。语气中立客观，结尾简短邀请用户开始。"
        ),
        "intro_template_en": (
            "Based on the user background below, write two to three sentences to introduce how the conversation will work: "
            "you will help the user map out the different information and interpretations around this topic "
            "so they get a clearer picture without drawing conclusions for them. Keep the tone neutral and objective, "
            "and briefly invite them to start."
        ),
    },
]

DEFAULT_TOPICS = [
    ("国家是否应该全面禁止销售香烟", "Should countries completely ban the sale of cigarettes?"),
    ("高中生应该把全部精力放在学习上，还是可以做兼职积累社会经验", "Should high school students focus entirely on studying, or can they work part-time to gain social experience?"),
    ("为了研发新的药物和治疗方法，是否应该使用动物进行实验", "Should animals be used in experiments to develop new medicines and treatments?"),
    ("全球变暖主要是由人类活动造成的吗", "Is global warming mainly caused by human activities?"),
    ("转基因食品是否应该被广泛生产和销售", "Should genetically modified foods be widely produced and sold?"),
    ("标准化考试是否能够公平地衡量学生的真实能力", "Can standardized tests fairly measure students' true abilities?"),
    ("智能机器人普及后，是否会导致大量人类失业", "Will the widespread use of intelligent robots lead to massive human unemployment?"),
    ("短视频平台是否能帮助青少年学习有价值的知识", "Can short-video platforms help teenagers learn valuable knowledge?"),
    ("自动驾驶汽车会让交通变得更加安全吗", "Will self-driving cars make traffic safer?"),
    ("美颜技术和滤镜的普及，会不会影响大众的审美观", "Will the popularity of beauty filters affect the public's aesthetic standards?"),
]

DEFAULT_SCALE_ITEMS = [
    ("emotion", "惊讶", "Surprised", 1, 5),
    ("emotion", "好奇", "Curious", 1, 5),
    ("emotion", "兴奋", "Excited", 1, 5),
    ("emotion", "困惑", "Confused", 1, 5),
    ("emotion", "焦虑", "Anxious", 1, 5),
    ("emotion", "挫败", "Frustrated", 1, 5),
    ("emotion", "无聊", "Bored", 1, 5),
    ("ai_eval", "AI 的回复有帮助", "The AI response was helpful", 1, 7),
    ("ai_eval", "AI 的回复保持了中立", "The AI response remained neutral", 1, 7),
]
