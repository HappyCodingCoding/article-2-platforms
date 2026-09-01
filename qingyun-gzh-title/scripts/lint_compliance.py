"""Compliance gate: word-surface check against 公众号 platform redlines.

Two severity tiers, because these words do not all behave the same way:

FAIL - an advertising-law or platform violation in essentially any context.
       Eliminated outright.
WARN - superlative-shaped, but with real descriptive uses. 第一批用户 is social
       proof, 一天里唯一不用回消息的时候 is a description, 从月薪 3 千到月入 5 万
       is personal history - while 唯一正确的方法 and 普通人也能月入过万 are
       violations. A human decides, and the note says on what basis.

Surface only. The semantic violations - unproven negative allegations about a
named party, 擦边, borrowing from a disaster, subjective experience presented
as objective effect - cannot be machine-judged and must be walked by hand
against the 9 redlines in references/scoring-and-redlines.md.

Called only by script.py.
"""

# Phrases that merely contain a superlative token but are ordinary language.
# Masked out before matching so 第一批 never reads as 第一.
EXEMPT_PHRASES = [
    "第一批", "第一次", "第一步", "第一时间", "第一天", "第一年", "第一份",
    "第一课", "第一反应", "第一眼",
]

# (category key, label, word list, severity, note / safe rewrite)
RULES = [
    (
        "absolute_hard",
        "极限词/绝对化用语",
        ["最好", "最强", "最佳", "最全", "最牛", "史上最", "全网最",
         "国家级", "世界级", "销量冠军", "百分百", "100%", "永久",
         "无一例外"],
        "FAIL",
        "把强度放进动词（彻底告别），或换成具体差异点",
    ),
    (
        "absolute_soft",
        "疑似绝对化用语",
        ["第一", "唯一", "最大", "最高", "顶级", "顶尖", "所有人都"],
        "WARN",
        "对产品或效果的绝对化宣称 → 淘汰；描述个人经历或客观事实序列 → 可留，但正文要能核",
    ),
    (
        "medical",
        "医疗功效断言",
        ["治疗", "治愈", "根治", "祛痘", "祛斑", "美白", "瘦身", "减肥药",
         "排毒", "抗炎", "消炎", "修复屏障", "生发", "抗癌", "特效", "药到病除"],
        "FAIL",
        "改写成主观感受与可观测现象（我用完的感受、上脸没闷痘）",
    ),
    (
        "income_hard",
        "收益承诺",
        ["稳赚", "包过", "保过", "躺赚", "零风险", "保本", "稳赚不赔",
         "包赚", "保证收益", "轻松月入"],
        "FAIL",
        "收益承诺没有安全改法，换一个公式",
    ),
    (
        "income_soft",
        "疑似收益承诺",
        ["月入过万", "日入过千", "月入 5 万", "月入5万"],
        "WARN",
        "写成「普通人也能月入过万」是承诺 → 淘汰；"
        "写成「我从月薪 3 千到月入 5 万」是个人经历 → 可留，且不得暗示可复制",
    ),
    (
        "traffic",
        "导流指令",
        ["加V", "加v", "加微", "私信领取", "私信我", "进群", "关注领",
         "关注领取", "扫码", "免费领", "领资料"],
        "FAIL",
        "导流不进标题，放到正文或菜单栏",
    ),
    (
        "clickbait",
        "恐吓式标题党",
        ["不看后悔一辈子", "99%的人都不知道", "99% 的人都不知道",
         "震惊", "速看速删", "马上删", "再不看就没了", "删前速看"],
        "FAIL",
        "把恐吓换成具体损失（错过再等 5 年）",
    ),
    (
        "minor",
        "未成年人容貌/身材评价",
        ["小学生身材", "初中生身材", "童模身材"],
        "FAIL",
        "不做涉及未成年人的容貌、身材评价类标题",
    ),
]


def lint(title):
    """Return the list of compliance hits, each carrying its own severity."""
    masked = title
    for phrase in EXEMPT_PHRASES:
        masked = masked.replace(phrase, "〇" * len(phrase))

    hits = []
    for key, label, words, severity, note in RULES:
        for w in words:
            if w in masked:
                hits.append({
                    "category": key,
                    "label": label,
                    "word": w,
                    "verdict": severity,
                    "fix": note,
                })
    return hits
