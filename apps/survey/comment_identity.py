COMMENT_IDENTITIES = (
    (1, "小兔"),
    (2, "小鸭"),
    (3, "小狐"),
    (5, "小狮"),
    (6, "小橙"),
    (7, "小鹅"),
)


def comment_avatar_file(index):
    avatar_number, _ = COMMENT_IDENTITIES[index % len(COMMENT_IDENTITIES)]
    return f"avatar{avatar_number}.png"


def comment_display_name(index):
    if index is None:
        return ""
    _, base_name = COMMENT_IDENTITIES[index % len(COMMENT_IDENTITIES)]
    cycle = index // len(COMMENT_IDENTITIES)
    return base_name if cycle == 0 else f"{base_name} {cycle + 1}"
