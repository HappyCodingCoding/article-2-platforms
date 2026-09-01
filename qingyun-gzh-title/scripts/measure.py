"""Length gate: measure a title against the 公众号 20-26 character budget.

Counting rule: 1 character costs 1 unit. Chinese characters, Latin letters,
digits, and punctuation are all worth the same. An emoji that renders as a
single glyph counts as 1, so ZWJ sequences, skin-tone modifiers, variation
selectors, keycaps, and regional-indicator pairs collapse into one unit.

Called only by script.py.
"""

import unicodedata

# Hard, inclusive budget. Anything outside it is eliminated.
MIN_CHARS = 20
MAX_CHARS = 26

# 公众号 keeps emoji restrained; more than one reads cheap in a subscription list.
EMOJI_CAP = 1

_ZWJ = "‍"
_VARIATION_SELECTORS = {"︎", "️"}
_SKIN_TONES = {chr(c) for c in range(0x1F3FB, 0x1F400)}
_KEYCAP = "⃣"


def _is_regional_indicator(ch):
    return "\U0001F1E6" <= ch <= "\U0001F1FF"


def _is_extender(ch):
    """True for characters that merge into the preceding grapheme cluster."""
    if ch in _VARIATION_SELECTORS or ch in _SKIN_TONES or ch == _KEYCAP:
        return True
    return unicodedata.category(ch) in ("Mn", "Me", "Mc")


def grapheme_clusters(text):
    """Split text into grapheme clusters.

    A close-enough approximation that avoids a third-party dependency.
    """
    clusters = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        cluster = ch
        i += 1
        # A pair of regional indicators is one flag.
        if _is_regional_indicator(ch) and i < n and _is_regional_indicator(text[i]):
            cluster += text[i]
            i += 1
        while i < n:
            nxt = text[i]
            if _is_extender(nxt):
                cluster += nxt
                i += 1
            elif nxt == _ZWJ and i + 1 < n:
                cluster += nxt + text[i + 1]
                i += 2
            else:
                break
        clusters.append(cluster)
    return clusters


def char_count(text):
    return len(grapheme_clusters(text))


def emoji_count(text):
    """Approximate count of emoji clusters, for the emoji quota check."""
    count = 0
    for cluster in grapheme_clusters(text):
        base = cluster[0]
        cp = ord(base)
        if (
            0x1F300 <= cp <= 0x1FAFF
            or 0x2600 <= cp <= 0x27BF
            or _is_regional_indicator(base)
            or (len(cluster) > 1 and _KEYCAP in cluster)
            or (len(cluster) > 1 and "️" in cluster)
        ):
            count += 1
    return count


def measure(title):
    """Return the length-gate result for one title.

    Spaces count like any other character, because they occupy budget in the
    published title. When a title only overflows because of the decorative
    spaces Chinese drafts put around numbers and Latin words, the note says
    so - deleting them is a free fix that costs no meaning.
    """
    n = char_count(title)
    tight = char_count("".join(title.split()))
    if n < MIN_CHARS:
        verdict = "FAIL"
        note = "%d 字，低于下限 %d，淘汰。别靠形容词凑长度——从简报里换一个更强的槽位" % (
            n, MIN_CHARS)
    elif n > MAX_CHARS:
        verdict = "FAIL"
        note = "%d 字，超出上限 %d，淘汰。删的应该是修饰语，不是承载信息的槽位" % (
            n, MAX_CHARS)
        if MIN_CHARS <= tight <= MAX_CHARS:
            note += "。注意：去掉 %d 个中英文间隔空格后为 %d 字，即可落回区间" % (
                n - tight, tight)
    else:
        verdict = "PASS"
        note = ""

    emojis = emoji_count(title)
    emoji_note = ""
    if emojis > EMOJI_CAP:
        emoji_note = "emoji %d 个，超过公众号上限 %d 个" % (emojis, EMOJI_CAP)

    return {
        "chars": n,
        "chars_without_spaces": tight,
        "range": "%d-%d" % (MIN_CHARS, MAX_CHARS),
        "verdict": verdict,
        "note": note,
        "emoji_count": emojis,
        "emoji_note": emoji_note,
    }
