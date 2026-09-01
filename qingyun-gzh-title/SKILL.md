---
name: qingyun-gzh-title
description: Drafts WeChat Official Account (微信公众号) article titles under a hard 20–26 character budget. Builds a content brief, picks a psychological trigger and one of the 8 爆款 formulas, assembles each candidate slot by slot, runs a length / compliance / AI-flavor gate script, scores and risk-grades the survivors, classifies them into five type-based tables sorted by score, then closes with A/B tests. Triggers on 「起标题」「公众号标题」「这篇文章叫什么好」「标题优化」「标题改写」「标题评分」「爆款标题」「10万+标题」. Modes - draft (title from content) and rewrite (diagnose and fix an existing title). Does not write body copy, make covers, or publish.
---

# WeChat Official Account Title Drafting

Turns one piece of content into a shortlist of 公众号 titles a reader stops for. Every candidate is assembled from named slots, held to a hard 20–26 character budget, and passed through three gates before it is allowed into the output.

Not one title — five type-sorted tables of them: multiple formulas, multiple mechanisms, filterable, A/B-ready.

**Core principles**

1. **A title's only job is the click, and the click must be honored.** It does not summarize the article; it opens a gap the article closes. Gaps are allowed, lies are not.
2. **Every slot must be earned by the content.** No number unless the body carries it, no 实测 unless it was tested, no 刚刚 unless it just happened, no 3 个方法 unless the body lists three.
3. **The AI-废稿 is a control group to read, not a thing to write.** Every formula in the reference has a paired version that looks complete and grabs nobody — 泛人群、无细节、空悬念、通用话术. Study it to recognize the failure mode in your own drafts; it is training material, and it never appears in the output.
4. **20–26 characters buys exactly three things.** An anchor, a tension, a payoff. If the content can only fill two, the title is weaker than its length suggests — say so rather than padding it to 26.

---

## Usage

The skill is callable by explicit options and by natural language alike — infer options and their values from the input regardless of typos, vague phrasing, or mixed Chinese/English. **When a value was inferred rather than stated, name the resolved options before running.** If no value can be inferred, or two fit equally well, ask instead of guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `--input` | option (required) | file path / article body / a topic / an existing title | — | The raw material. A file path is read from disk. A single short line the user wants "改改" or "优化" normally means `--mode rewrite`. |
| `--mode` | option | `draft` / `rewrite` | inferred from `--input` | `draft` writes new titles from content. `rewrite` diagnoses a title the user already has, then rewrites it while preserving its working assets. A full article or a topic → `draft`; one short line plus a request to improve it → `rewrite`. |
| `--action` | option | `click` / `share` / `comment` / `save` / `auto` | `auto` | The reader behavior this title is optimized for; it decides which psychological triggers get priority. `auto` = infer from content type and state the basis for the inference. |
| `--count` | option | integer 6–20 | `10` | How many candidates to generate. Below 6 cannot cover enough formulas; above 20 only produces near-duplicates. |
| `--subtitle` | option | `on` / `off` | `off` | `on` additionally pairs cluster winners into 主标题｜副标题 combinations — 公众号 supports a second line, 小红书 does not. Turn on for 干货 and 方法论 pieces where the emotional hook and the concrete payoff will not both fit in 26 characters. |

---

## Workflow

### Step 1 — Resolve the input and the options

Determine the shape of `--input` (file / body text / topic / existing title) and resolve every option value. List every value that was inferred rather than stated, e.g. `识别为 --mode draft --action share --count 10`.

If `--input` is a file path, read it in full first. If `--input` is a bare topic — one line, no material behind it — do not invent material to compensate. Go to Step 2, mark most brief fields 缺, and carry that limitation into the output at Step 11.

### Step 2 — Build the content brief

Read the content and extract the fields below. **Mark missing fields 缺; never fabricate one.** The brief is what every later step draws from — a title that references anything not in this brief is out of bounds.

- **核心对象** — the single highest-traffic concrete entity (product / person / company / method / place). One strong entity beats three weak ones stacked.
- **人群行为标签** — not the demographic label, the daily action. Not 宝妈 but 每天 6 点起床给娃做早餐的宝妈; not 职场人 but 天天加班到 10 点还被骂效率低的打工人. **This is the most valuable line in the brief.** A bare demographic label is the single clearest AI tell.
- **反常识点** — the thing this reader does every day, believes is right, and gets no result from. What breaks it?
- **可兑现的结果** — what the reader gets or avoids, and how far the body can actually prove it.
- **证据资产** — real numbers, prices, durations, before/after pairs, verbatim complaints, real dialogue. Pull these out first; they outrank every adjective available.
- **冲突张力** — old vs new, gain vs loss, expectation vs reality, who is against whom.
- **情绪基调** — 崩溃 / 惊喜 / 解气 / 治愈 / 好奇 / 警惕 / 认同.
- **时效等级** — 即时热点 / 节点季节性 / 常青. Only 即时热点 earns 刚刚 and 今天凌晨.
- **事实边界** — conclusions, numbers, effects, rankings, and absolutes the body does **not** prove. Nothing on this line may enter a title.
- **合规风险点** — whether the piece touches 医疗 / 功效 / 投资收益 / 未成年人 / 点名贬损.

### Step 3 — Diagnose the existing title (`--mode rewrite` only)

If `--mode draft`, skip Step 3 and continue to Step 4.

Check the user's title against each item and mark 有 / 无: character count inside 20–26 / a concrete entity or behavior-anchored 人群 / a broken assumption or tension / a payoff the reader can name / plain spoken register rather than 书面腔 / any 极限词 or 违规词. Then state the **保留资产** explicitly — a good verb, a real number, an accurate 人群 word — and do not let the rewrites delete them.

### Step 4 — Fix the target action, then pick the psychological trigger

The action decides the trigger; the trigger decides which nerve the title touches. With `--action auto`, infer the action from the content type and say what the inference rests on.

| `--action` | Priority triggers |
|---|---|
| `click` | 好奇、捷径、悬念 |
| `share` | 态度、共愤、幽默、从众 |
| `comment` | 共愤、避坑、态度 |
| `save` | 清单、希望、避坑、治愈 |

Full definitions, psychological basis, how each one lands specifically on 公众号, the Chinese word banks, and per-trigger redlines: read `references/psych-triggers.md`.

One title carries **one primary trigger, at most one secondary**. A trigger expresses what the content already is — if the piece has no 希望感 in it, do not bolt 希望 onto the title.

### Step 5 — Route the content type to formulas

The trigger decides which nerve; the formula decides the sentence shape 公众号 readers are used to being asked in. Look up the content type in the routing table and take its preferred and its ill-suited formulas.

Read `references/title-formulas.md` for the 8 core formulas (each with slot breakdown, 爆款 examples, its matching AI-废稿 to recognize and avoid, and a formula-specific de-AI tactic), the 6 supplementary corpus methods, the routing table, the 加辣 enhancers, and the formula-stacking rules.

### Step 6 — Assemble `--count` candidates, slot by slot

**Before drafting a single candidate, read `references/de-ai-writing.md`.** This is not optional and not a one-time read to remember from an earlier session — do it every time this step runs. It is not a checklist to run against a finished title afterward; nothing later in this workflow checks it, not the gate script at Step 8, not anywhere else. It is how a title is supposed to sound *while being written*, not a filter applied after. Read it, then draft with that register already in mind.

Generate `--count` candidates covering **at least 5 different formulas** and **at least `⌈--count ÷ 2⌉` distinct primary psychological mechanisms** (capped at 10 — `references/psych-triggers.md` defines exactly 10), with **no single mechanism as the primary on more than `⌊--count × 0.3⌋` candidates** (minimum 1). At the default `--count 10` that is 5 distinct mechanisms, none used more than 3 times; at `--count 6` it is 3 distinct, none more than 1 time; at `--count 20` it is all 10 mechanisms, none more than 6 times. Do not write ten variations of one pattern — in formula, or in mechanism.

A formula-diverse set can still be mechanism-collapsed — 10 different sentence shapes all pulling the same lever (好奇, most often) passes the formula count and fails the point of the trigger layer. Track both tallies as you generate, not after.

Assemble each one against the three-slot budget rather than writing a sentence and measuring it afterwards:

| Slot | What goes in it | Rough budget |
|---|---|---|
| ① 锚点 | 人群行为标签 or 核心对象 — who this is for, or what this is about | 6–12 chars |
| ② 张力 | 反常识点 / 冲突 / 反常细节 / 数字反差 — the reason to keep reading | 6–10 chars |
| ③ 兑现 | 结果预期 / 灵魂反问 / 留白 — what clicking gets them | 4–8 chars |

Three filled slots is what earns 26 characters. Two filled slots should produce a **shorter** title, not a padded one — but the floor is 20, so a two-slot idea that cannot reach 20 characters honestly needs a stronger slot from the brief, not filler adjectives.

Record the slot breakdown for every candidate; it is reported at Step 11 and it is what makes a weak candidate diagnosable.

**Only use a formula the body supports.** No number without a number in the brief, no 实测 without a real trial, no 刚刚 unless 时效等级 is 即时热点, no 官宣 unless it is official.

### Step 7 — Season and stack

Apply the 加辣 enhancers (`references/title-formulas.md`, final section) candidate by candidate; they stack. Then try stacking formulas — 爆款 titles are frequently two formulas layered, e.g. 《从月薪3千到月入5万，我其实只做对了2件事》 is 数字聚焦 + 悬念钩子.

**Seasoning does not add facts.** It changes how a thing is said, never adds something the body does not contain. Re-check the length budget after seasoning — enhancers add characters.

### Step 8 — Run the gate script

Write every candidate to a plain text file, one per line, then run:

```bash
python3 qingyun-gzh-title/scripts/script.py --titles-file <候选文件路径>
```

Add `--json` for structured output. The script reports:

1. **字符闸** — counts 1 per character, Chinese and English letters, digits, punctuation, and spaces alike; an emoji that renders as one glyph counts as 1. Outside **20–26 inclusive** → **FAIL, eliminated**. When a title only overflows because of the decorative spaces a draft puts around numbers and Latin words, the script says so — deleting them costs no meaning and is the first fix to try.
2. **合规闸** — two tiers. 极限词、医疗功效断言、硬性收益承诺、导流指令、恐吓式标题党 → **FAIL, eliminated**. Superlative-shaped words with real descriptive uses (第一、唯一、月入过万) → **WARN**: a claim about a product or an effect is eliminated, a description of personal history or an observed fact may stay if the body can back it. The script names the word and the test; **the ruling is yours to make and to state.**
3. **泛人群标签** — a bare demographic label with no behavior anchor in front of it (WARN, fix by hand or justify). This is the only style-level check the script runs, and it is narrow on purpose — one standing exemption: 情绪共鸣型 is built on the group's own self-label, so cite the formula and keep it.

**None of the 8 de-AI rules run here, and none of them ever will — no script can judge template-assembly feel, sentence rhythm, or whether a title holds a point of view.** That judgment already happened before this step, at Step 6, by reading `references/de-ai-writing.md` before drafting. This gate is not where de-AI checking lives; it is where length, compliance, and one narrow label pattern get caught mechanically. If a candidate reads AI-flavored at this point, that is a Step 6 problem to fix by regenerating with the reference reread, not something this script will ever flag.

Regenerate replacements for every FAIL back up to `--count`, then re-run this step until nothing fails.

### Step 9 — Score, dedupe, risk-grade, classify into types

**Check the mechanism spread against `--action` first.** Tally the primary mechanism of every surviving candidate and compare it to the priority-trigger row resolved at Step 4. If most candidates sit outside that row, something drifted — either `--action` was resolved wrong at Step 1 (state the correction and re-resolve) or generation ignored it despite Step 6's coverage rule (regenerate the candidates that don't fit). Do not silently ship a set that argues against its own declared action.

Score every survivor dimension by dimension using the rubric in `references/scoring-and-redlines.md` — **do not report a total by feel**. Then cut: anything the body cannot honor, anything that is a one-word variant of another candidate, anything that only works if the reader misunderstands it.

Grade each remaining candidate 低 / 中 / 高 risk.

**Classify every surviving candidate into exactly one of the five types below** — the type it fits best, not every type it could plausibly serve. This is a strict partition: each candidate lives in one cluster only.

1. **综合型** — best balance of click pull and credibility
2. **稳健型** — clearest information, safe for a brand or professional account
3. **传播型** — strongest conflict, reversal, or emotion; optimized for forwarding
4. **搜索型** — entity and keywords intact, for 微信搜一搜 discovery
5. **实验型** — newest structure, widest gap, for a small A/B

**No cluster may be empty.** If nothing distinctly fits a type, assign the least-bad candidate to it anyway — its score and risk columns in Output ② will read lower than the other clusters' winners, and that visible gap is the signal. No prose flags it.

Within each cluster, sort by score and apply two promotion gates before the top row is settled:

- **高风险 cannot win 综合型.** If the highest-scoring candidate in the 综合型 cluster is 高风险, skip it for the top row and promote the next-highest-scoring 低/中风险 candidate in that cluster instead. The other four types carry no such restriction — 传播型 in particular is often the higher-risk pick by nature, and that is expected, not a defect.
- **三秒闸.** A candidate that fails any of the three questions below cannot be a cluster's top row — promote the next-best candidate in that cluster instead:
  1. Can the reader tell in 1 second that this is written for them?
  2. Can they feel in 1 second that it solves their pain or delivers their reward?
  3. Will they feel that not clicking costs them something?

If the brief was thin (Step 1 flagged a bare topic, or more than half the brief is 缺), ship the conservative set and **state explicitly what was missing and how it capped the strength** — do not close the gap with invention.

### Step 10 — Build 主标题｜副标题 pairs (`--subtitle on`)

If `--subtitle off`, skip Step 10 and continue to Step 11.

Pair cluster winners (the top row of any table from Step 9) into 主标题 + 副标题, split by `｜`: 主标题 carries the emotion or the reversal, 副标题 delivers the concrete payoff — 《真正厉害的人都学会了反内耗｜3个方法，停止精神内耗》（25 字）.

**The 20–26 budget applies to the combined string, separator included**, because that whole string is what publishes as the title. In practice that leaves roughly 12 characters a side, so a pair is only worth building when both halves are genuinely short — a 24-character 主标题 has no room for a 副标题 and should ship on its own. Build 2–3 pairs, not more.

### Step 11 — Render the result per the Output section

---

## Output

All reader-facing labels, titles, and rationale are written in Chinese; the finished titles are 公众号 copy.

### ① 内容简报

5–8 lines: 核心对象、**人群行为标签**、反常识点、可兑现的结果、可用证据、情绪基调与时效等级、事实边界与合规边界. Mark 缺 fields as 缺. With `--mode rewrite`, precede it with the Step 3 diagnosis and the 保留资产 list.

### ② 候选标题矩阵（五组，按 Step 9 分类，组内按评分从高到低排序，编号跨组连续）

Five tables, one per type, in this fixed order: 综合型 → 稳健型 → 传播型 → 搜索型 → 实验型. Each candidate appears in exactly one table — the type it was classified into at Step 9 — sorted by 评分 high to low within that table.

**`#` is one running sequence across all five tables**, not reset per table — 综合型's rows continue straight into 稳健型's numbering, and so on. Every candidate gets one stable number regardless of which table it sits in, so it can be referenced by number alone in ③.

| # | 候选标题 | 字数 | 心理机制 | 公式 | 槽位拆解（锚点/张力/兑现） | 点击钩子 | 评分 | 风险 |
|---|---|---:|---|---|---|---|---:|---|

Use the standard trigger and formula names from the reference files; write a stacked one as 主公式 + 辅公式. 槽位拆解 shows which of the three slots each candidate actually fills — an empty slot is written 空. Every 中 or 高 风险 entry, in any table, states its reason in the 风险 column. No prose commentary beyond the table — the score and risk columns carry the judgment.

### ③ Top 5 一览

One bullet per type, in fixed order (综合型 → 稳健型 → 传播型 → 搜索型 → 实验型), each referencing its cluster's `#1` from ② by number rather than repeating the full row:

`**{角色}** — #{编号}《{候选标题}》（{字数} 字）— {心理机制}，{风险}，{一句理由}。`

The one-sentence reason names why this candidate won its cluster; for a weak cluster (Step 9's no-empty-cluster fallback), say so plainly instead of overselling it. This is the only place in the output that carries prose reasoning — ② stays table-only.

### ④ 双标题组合（`--subtitle on`）

| 主标题（字数） | 副标题 | 合计字数 | 主标题抓的情绪 | 副标题给的价值 |
|---|---|---:|---|---|

### ⑤ A/B 测试建议

2–3 pairs, each changing **exactly one variable**, each with its hypothesis and the metric that settles it: 有数字 vs 无数字 / 问句 vs 判断句 / 人群前置 vs 结果前置 / 克制词 vs 强张力词. Keep publish time and cover style constant across the pair, or the variable is not alone.

### ⑥ 兑现提示（one line）

Does the promise the title actually chosen for publication make appear in the first three lines of the article? A title's gap must start closing immediately — 公众号 readers who scroll past the opening without seeing it do not return.

---

## Gotchas

- **20–26 is a hard gate, not a target.** The script eliminates anything outside it. 19 characters is not "close enough" and 27 is not "slightly long" — regenerate rather than trimming a character off a word that was carrying meaning.
- **A padded 26 is worse than an honest 22.** Length is only earned by filled slots. Adjectives added to reach the floor are exactly the AI tell this skill exists to remove.
- **A bare demographic label reads as AI even when everything else is right.** 宝妈、职场人、年轻人、普通人 alone are the tell, and the fix is a behavior, never a stronger adjective. The one exception is 情绪共鸣型, which is built on the group's own self-label (80 后、成年人) — there the bare label is the formula, so cite it and keep it.
- **Numbers are not automatically strong.** Only about 30% of 10万+ titles carry one, while about 66% carry a concrete entity. Anchor an entity first; reach for a number only when the gap between two of them does the work (`从月薪3千到月入5万`).
- **公众号 has almost no search long tail.** Unlike 小红书, a 公众号 title lives or dies on first-send and forwarding, so emotion and conflict outrank keyword coverage — but keep the core entity intact for 搜一搜.
- **emoji are a restraint item here**, 0–1 at most. What reads as native on 小红书 reads as cheap in a 公众号 subscription list.
- **热点 titles expire, the 观点 half does not.** In `热点 + 观点` the colon is the dividing line: the first half borrows traffic, the second half is the part worth being remembered for. Never borrow from 灾难 or 公共安全 events.
- **Formula variety hides mechanism collapse.** Ten different 公式 can still all be running on 好奇 — an information-gap engine dressed in ten sentence shapes. Formula and mechanism are independently trackable and Step 6 checks both; hitting the formula count is not evidence the mechanism count is fine.
- **评分 only orders candidates within their own table.** 传播型's `#1` can outscore 综合型's `#1` and that is not a defect — the five tables answer five different questions, and a type's winner is whichever candidate fits that type best, not whichever candidate has the highest score anywhere in the whole pool.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only, no third-party packages.