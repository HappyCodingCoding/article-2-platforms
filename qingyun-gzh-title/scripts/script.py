#!/usr/bin/env python3
"""Main script for the qingyun-gzh-title skill: runs all three gates in one pass.

Usage:
    python3 script.py --titles-file candidates.txt
    python3 script.py --titles-file candidates.txt --json

Candidate file format: one title per line. Blank lines and lines starting
with # are ignored. A leading `1. `, `- `, or `gzh: ` is stripped, so a list
pasted straight out of the draft still works.

Reports the length gate (measure), the compliance gate (lint_compliance), and
a narrow bare-demographic-label check (lint_aiflavor) - not the 8 de-AI rules,
none of which are machine-checkable. Those are read by the agent before
drafting, at Step 6, from references/de-ai-writing.md; nothing here checks
them. A FAIL is eliminated - regenerate replacements and re-run. Exits 1 when
anything failed.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lint_aiflavor
import lint_compliance
import measure

# Leading list markers a pasted draft tends to carry.
_PREFIX = re.compile(r'^(?:gzh[:：]\s*|\d+[.、)）]\s*|[-*]\s*)')
# Title brackets are presentation, not part of the character budget.
_BRACKETS = ("《》", "「」", "“”", '""')


def clean(line):
    """Strip list markers and outer title brackets from one candidate line."""
    line = _PREFIX.sub("", line.strip())
    for pair in _BRACKETS:
        if len(line) >= 2 and line[0] == pair[0] and line[-1] == pair[1]:
            line = line[1:-1].strip()
            break
    return line


def parse_titles(path):
    """Read the candidate file and return a list of titles."""
    titles = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            title = clean(line)
            if title:
                titles.append(title)
    if not titles:
        raise SystemExit("候选文件里没有可用的标题行")
    return titles


def check(title):
    """Run all three gates over one title and merge the results."""
    m = measure.measure(title)
    compliance = lint_compliance.lint(title)
    aiflavor = lint_aiflavor.lint(title)

    hard_compliance = [h for h in compliance if h["verdict"] == "FAIL"]
    if m["verdict"] == "FAIL" or hard_compliance:
        verdict = "FAIL"
    elif compliance or m["emoji_note"] or aiflavor:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "title": title,
        "verdict": verdict,
        "measure": m,
        "compliance": compliance,
        "aiflavor": aiflavor,
    }


def reasons(row):
    """Flatten one result into human-readable disposition lines."""
    out = []
    if row["measure"]["note"]:
        out.append("[字符] " + row["measure"]["note"])
    if row["measure"]["emoji_note"]:
        out.append("[字符] " + row["measure"]["emoji_note"])
    for hit in row["compliance"]:
        disposition = "淘汰" if hit["verdict"] == "FAIL" else "待判断"
        out.append("[合规] %s「%s」%s → %s" % (
            hit["label"], hit["word"], disposition, hit["fix"]))
    for w in row["aiflavor"]:
        out.append("[AI味] %s「%s」——%s" % (w["rule"], w["detail"], w["note"]))
    return out


def render(rows):
    lines = [
        "",
        "## 三道闸结果（公众号，硬性区间 %d–%d 字）" % (
            measure.MIN_CHARS, measure.MAX_CHARS),
        "",
        "| # | 候选标题 | 字数 | emoji | 判定 |",
        "|---|---|---:|---:|---|",
    ]
    for i, r in enumerate(rows, 1):
        lines.append("| %d | %s | %d | %d | %s |" % (
            i, r["title"].replace("|", "\\|"),
            r["measure"]["chars"], r["measure"]["emoji_count"], r["verdict"]))

    detail = [(i, r) for i, r in enumerate(rows, 1) if reasons(r)]
    if detail:
        lines.append("")
        for i, r in detail:
            lines.append("**%d. %s** — %s" % (i, r["title"], r["verdict"]))
            for reason in reasons(r):
                lines.append("  - " + reason)

    n_fail = sum(1 for r in rows if r["verdict"] == "FAIL")
    n_warn = sum(1 for r in rows if r["verdict"] == "WARN")
    lines += [
        "",
        "小计：%d 条，PASS %d / WARN %d / FAIL %d" % (
            len(rows), len(rows) - n_fail - n_warn, n_warn, n_fail),
        "",
        "---",
        "FAIL 直接淘汰，补生成后重跑本脚本。WARN 需人工判断后修正或写明保留理由。",
        "去 AI 味 8 条全部是语义层，脚本一条都不查——起草前先读",
        "references/de-ai-writing.md 内化写法，而不是写完再靠脚本挑错。",
        "脚本这里只查了一件窄事：泛人群标签有没有行为限定，不代表候选已经过了 AI 味关。",
        "红线里的擦边、蹭灾难热点、未证实的负面指控、把主观感受写成客观效果也是语义层——都要人工过。",
        "另外脚本查不出槽位：每条候选的「锚点 / 张力 / 兑现」三槽填了几个，要自己标。",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="qingyun-gzh-title gates: length / compliance / bare demographic label")
    ap.add_argument("--titles-file", required=True,
                    help="candidate file, one title per line")
    ap.add_argument("--json", action="store_true",
                    help="emit structured JSON instead of a markdown table")
    args = ap.parse_args()

    if not os.path.isfile(args.titles_file):
        raise SystemExit("找不到候选文件：%s" % args.titles_file)

    rows = [check(title) for title in parse_titles(args.titles_file)]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(render(rows))

    if any(r["verdict"] == "FAIL" for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
