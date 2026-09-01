"""Bare-demographic-label check.

Not one of the 8 de-AI rules (references/de-ai-writing.md) — none of those
are machine-checkable, and none of them run here or anywhere else in this
script. All 8 are read by the agent before drafting (Step 6), not checked
after. This module covers a single, separate, mechanically clean signal: a
demographic label with no behavior anchor in front of it, which is the
clearest AI tell 痛点直击型 specifically turns on (see
references/title-formulas.md).

Every finding here is a WARN. Fix it, or state why the title keeps it.

Called only by script.py.
"""

# Demographic labels that read as AI whenever they arrive without a behavior
# anchor in front of them. See 痛点直击型 in references/title-formulas.md.
PERSON_TAGS = [
    "宝妈", "全职妈妈", "二胎妈妈", "职场人", "打工人", "上班族", "年轻人",
    "中年人", "成年人", "普通人", "新手", "小白", "大学生", "毕业生",
    "家长", "父母", "创业者", "自由职业者", "女人", "男人", "女生", "男生",
]


def _anchored(title, idx):
    """True when the demographic label at idx carries a qualifier in front.

    Anchored means either a behavior clause ending in 的
    (天天加班到 10 点的打工人) or a numeric qualifier within the preceding
    four characters (30 岁职场人).
    """
    prefix = title[max(0, idx - 4):idx]
    if prefix.endswith("的"):
        return True
    return any(ch.isdigit() for ch in prefix)


def lint(title):
    """Return the list of bare-demographic-label warnings. All are WARN."""
    warns = []

    for tag in PERSON_TAGS:
        idx = title.find(tag)
        if idx >= 0 and not _anchored(title, idx):
            warns.append({
                "rule": "泛人群标签",
                "detail": tag,
                "note": "泛标签没有行为或限定，是痛点直击型最明显的 AI 破绽——"
                        "换成简报里的人群行为标签（行为 + 的 + %s）。"
                        "例外：情绪共鸣型用的就是群体自称，此时可保留" % tag,
            })

    return warns
