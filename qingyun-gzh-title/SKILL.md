---
name: qingyun-gzh-title
description: Drafts WeChat Official Account (微信公众号) article titles under a hard 20–26 character budget. Builds a content brief, scores and pairs psychological triggers with 爆款 formulas into a tactic list, drafts and gates each candidate tactic by tactic (length, compliance, demographic-label, and three-second-hook checks), scores and risk-grades the survivors, classifies them into five type-based tables sorted by score, then closes with A/B tests. Triggers on 「起标题」「公众号标题」「这篇文章叫什么好」「标题优化」「标题改写」「标题评分」「爆款标题」「10万+标题」. Modes - draft (title from content) and rewrite (diagnose and fix an existing title). Does not write body copy, make covers, or publish.
---

# WeChat Official Account Title Drafting

Turns one piece of content into a shortlist of 公众号 titles a reader stops for. Every candidate is drafted from a scored formula+trigger tactic, held to a hard 20–26 character budget, swept for AI-sounding patterns, and gated on length, compliance, and hook clarity before it is allowed into the output.

Not one title — five type-sorted tables of them: multiple formulas, multiple mechanisms, filterable, A/B-ready.

**Core principles**

1. **A title's only job is the click, and the click must be honored.** It does not summarize the article; it opens a gap the article closes. Gaps are allowed, lies are not.
2. **Every slot must be earned by the content.** No number unless the body carries it, no 实测 unless it was tested, no 刚刚 unless it just happened, no 3 个方法 unless the body lists three.
3. **The AI-废稿 is a control group to read, not a thing to write.** Every formula in the reference has a paired version that looks complete and grabs nobody — 泛人群、无细节、空悬念、通用话术. Study it to recognize the failure mode in your own drafts; it is training material, and it never appears in the output.
4. **20–26 characters is earned by the chosen formula's own parts, never padded to reach it.** Formulas differ in how many parts they have — three for some, two or one for others (see `references/title-formulas.md`). A title that falls short needs a stronger part pulled from the brief, not a filler adjective; say so rather than padding it to 26.

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

Work every step below in full, in order — do not skip one, merge two into one pass, or shortcut the diligence a step calls for to save time. `### ⑥ 流程审计` in the Output exists to hold you to this: it records what actually happened at each step, not a plausible-looking summary backfilled after the fact — a step skipped or rushed has nothing honest to report there.

### Step 1 — Resolve the input and the options

Determine the shape of `--input` (file / body text / topic / existing title) and resolve every option value. List every value that was inferred rather than stated, e.g. `识别为 --mode draft --action share --count 10`.

If `--input` is a file path, read it in full first. If `--mode draft` and the source already carries its own title (a document heading, a page title, a working title at the top of the file), ignore it — do not let it anchor Step 2's brief or bias which triggers or formulas look like the obvious fit. Analyze and draft from the body alone, as if it arrived untitled; this does not apply to `--mode rewrite`, where the existing title is the thing being diagnosed. If `--input` is a bare topic — one line, no material behind it — do not invent material to compensate. Go to Step 2, mark most brief fields 缺, and carry that limitation into the output at Step 11.

### Step 2 — Build the content brief

Read the content and extract the fields below. **Mark missing fields 缺; never fabricate one.** The brief is what every later step draws from — a title that references anything not in this brief is out of bounds.

- **核心对象** — the single highest-traffic concrete entity (product / person / company / method / place). One strong entity beats three weak ones stacked.
- **人群行为标签** — not the demographic label, the daily action. Not 宝妈 but 每天 6 点起床给娃做早餐的宝妈; not 职场人 but 天天加班到 10 点还被骂效率低的打工人. **This is the most valuable line in the brief.** A bare demographic label is the single clearest AI tell.
- **反常识点** — the thing this reader does every day, believes is right, and gets no result from. What breaks it?
- **读者回报** — what the reader gets or avoids, and how far the body can actually prove it.
- **证据资产** — real numbers, prices, durations, before/after pairs, verbatim complaints, real dialogue. Pull these out first; they outrank every adjective available.
- **冲突张力** — old vs new, gain vs loss, expectation vs reality, who is against whom.
- **情绪基调** — 崩溃 / 惊喜 / 解气 / 治愈 / 好奇 / 警惕 / 认同.
- **时效等级** — 即时热点 / 节点季节性 / 常青. Only 即时热点 earns 刚刚 and 今天凌晨.
- **事实边界** — conclusions, numbers, effects, rankings, and absolutes the body does **not** prove. Nothing on this line may enter a title.
- **合规风险点** — whether the piece touches 医疗 / 功效 / 投资收益 / 未成年人 / 点名贬损.

### Step 3 — Diagnose the existing title (`--mode rewrite` only)

If `--mode draft`, skip Step 3 and continue to Step 4.

Check the user's title against each item and mark 有 / 无: character count inside 20–26 / a concrete entity or behavior-anchored 人群 / a broken assumption or tension / a payoff the reader can name / plain spoken register rather than 书面腔 / any 极限词 or 违规词. Then state the **保留资产** explicitly — a good verb, a real number, an accurate 人群 word — and do not let the rewrites delete them.

### Step 4 — Infer the target action, then score and rank psychological triggers

With `--action auto`, infer the action from the content type and state what the inference rests on; otherwise use the resolved `--action` directly.

| `--action` | Priority triggers |
|---|---|
| `click` | 好奇、捷径、悬念 |
| `share` | 态度、共愤、幽默、从众 |
| `comment` | 共愤、避坑、态度 |
| `save` | 清单、希望、避坑、治愈 |

Read `references/psych-triggers.md` for the 10 mechanisms. Each entry's **Basis** gives the psychological grounding, **Action** names what the reader does once triggered, **Content prerequisite** tells you whether this piece actually qualifies (a trigger the content doesn't earn does not get bolted on), **公众号 landing** shows how it lands specifically here, **词库** is the word bank to draw one term from, **Redline** is what breaks it.

Score every trigger's fit to the brief on a 1–10 scale, using Basis + Content prerequisite + Action. **A trigger is genuinely suited only at a score of 6 or higher** — below that it does not enter the pool, however plausible it looks. Pick every trigger that clears the bar, at least `⌈--count ÷ 2⌉` (capped at 10, since there are only 10); if fewer than the floor clear it even after scoring all 10, use everything that does and note the shortfall in Output ① rather than lowering the bar. Rank the pool highest to lowest. This ranked pool, not the full 10, is what Step 6 draws from.

### Step 5 — Route the content type to formulas

Read `references/title-formulas.md` for its 19 formulas — one flat list, no tier between them. Each entry's **Core logic** explains why it works, **公式** states its parts, **前提** (where present) states the one precondition that must hold before the formula is even eligible, **Slots** elaborates what each part needs and the test for whether it's earning its place, **范例** shows verified positive examples, **AI 废稿** and **De-AI tactic** (where present) show the failure mode to recognize and the formula-specific way to keep it human, **Redline** is what breaks it.

Score every formula's fit to the brief on a 1–10 scale, using Core logic — and where a formula states a **前提**, treat it as a hard filter first: a formula whose precondition the brief doesn't meet is not genuinely suited no matter how well it would otherwise score. **A formula is genuinely suited only at a score of 6 or higher** — below that it does not enter the pool, however plausibly it could apply. Pick every formula that clears the bar, at least `⌈--count ÷ 2⌉`, from the full set of 19. If fewer than the floor clear the bar even after scoring all 19, use everything that does and note the shortfall in Output ① rather than lowering the bar. Rank the pool highest to lowest.

### Step 6 — Pair formulas with triggers into a tactic manifest

One **tactic** = one formula + one trigger. Build the full grid: the best-ranked formula paired with every trigger in the Step 4 pool (best to worst), then the second-ranked formula paired with every trigger, and so on through the ranked formula pool. Score each cell as the formula's Step 5 score plus the trigger's Step 4 score.

Select the top `--count` cells by that combined score — but cap diversity while selecting: **no single formula, and no single trigger, may be used in more than `⌊--count × 0.3⌋` (minimum 1) of the chosen tactics.** When the next-best cell by score would breach either cap, skip it and take the next-best cell that doesn't. At `--count 10` that is a cap of 3 per formula and per trigger — a trigger that scores well against everything still can't fill more than 3 of the 10 tactics.

The Step 4/5 floors (`⌈--count ÷ 2⌉` triggers, `⌈--count ÷ 2⌉` formulas selected into their pools) guarantee the grid always has at least `--count` distinct cells, so this selection never needs to be padded by reusing a tactic already chosen.

Order the final `--count` tactics by score, highest to lowest. This ordered list is what Step 8 drafts against, one tactic per candidate.

### Step 7 — Learn how to De-AI writing

**Before drafting a single candidate, read `references/de-ai-writing.md`.** Not optional, not something to skip because it was already read once — every run. These 6 rules are non-formula-specific and non-trigger-specific; they apply to every candidate regardless of which tactic produced it. Each rule pairs a failure pattern with why it reads as AI and a verified ❌/✅ example. Internalize the register before drafting, not after — nothing later in this workflow checks these rules mechanically.

### Step 8 — Draft titles tactic by tactic until `--count` titles are drafted successfully

Work through the Step 6 tactic list in order. For each tactic:

1. **Draft.** Write one title using the tactic's trigger (公众号 landing, 词库, Redline) and formula (公式, Slots, 范例, AI 废稿, De-AI tactic, Redline), with the Step 7 register already in mind. **Only use a formula or trigger the body actually supports** — no number without one in the brief, no 实测 without a real trial, no 刚刚 unless 时效等级 is 即时热点.

2. **Season and stack.** Only when the draft is under 26 characters and a change would genuinely strengthen it: stack a second formula first (`references/title-formulas.md`, `## Formula stacking` — two at most, preferring a formula already in the Step 5 ranked pool), then apply `## 加辣 enhancers` word-level seasoning on top of whatever formula(s) the title now carries. Re-measure after each change — both cost characters, and 26 is a hard ceiling that neither may cross.

3. **De-AI check and rewrite.** Sweep the draft against `references/de-ai-writing.md`'s 6 rules, one by one: does it match the rule's ❌ pattern, or does it read like the ✅ one? Wherever it matches a ❌ pattern, rewrite that part per the rule's own guidance, then sweep all 6 again — a rewrite for one rule can trip another. After 3 full sweeps, stop: keep the best version and state plainly which rule(s) it still fails, if any, so the next sub-step and the output don't silently launder a title that never actually passed. 情绪共鸣型's own group self-label is still the standing exemption to Rule 3, but only when that label predates the article — a term the piece just coined doesn't qualify and needs the anchor like any other formula.

4. **Gate the single title.** Run it (alone, or batched with a few other freshly drafted candidates) through `python3 qingyun-gzh-title/scripts/script.py --titles-file <候选文件路径>` for the two mechanical checks, and judge the remaining one by reasoning. Redraft the same tactic if it fails any of the three:
   - **字符闸** (script) — 20–26 characters inclusive.
   - **合规闸, hard tier only** (script) — the eliminated-outright redlines in `references/scoring-and-redlines.md`. The soft/WARN tier (第一、唯一 and similar) does **not** force a redraft here — carry it forward to Step 9 for a human ruling.
   - **三秒闸** (reasoning) — can the reader tell in 1 second this is written for them; can they feel in 1 second it solves their pain or delivers their reward; will not clicking cost them something. One unanswerable question fails the gate.

   **After 3 failed attempts on the same tactic, stop redrafting it.** Keep the best of the 3 and carry it forward — but state plainly which gate(s) it still fails, if any, so Step 9 and the output don't silently launder a title that never actually passed.

Continue until `--count` titles have been drafted (each either clean, or carrying a flagged best-of-3 from sub-step 3 or 4).

### Step 9 — Score, dedupe, risk-grade, classify into types

Score every survivor dimension by dimension using the rubric in `references/scoring-and-redlines.md` — **do not report a total by feel**. Then cut: anything the body cannot honor, anything that is a one-word variant of another candidate, anything that only works if the reader misunderstands it.

Grade each remaining candidate 低 / 中 / 高 risk.

**Classify every surviving candidate into exactly one of the five types below** — the type it fits best, not every type it could plausibly serve. This is a strict partition: each candidate lives in one cluster only. Note each candidate's second-best-fit type as you go; it is not shown anywhere in the output, but it is what the no-empty-cluster fallback below draws on.

1. **综合型** — best balance of click pull and credibility
2. **稳健型** — clearest information, safe for a brand or professional account
3. **传播型** — strongest conflict, reversal, or emotion; optimized for forwarding
4. **搜索型** — entity and keywords intact, for 微信搜一搜 discovery
5. **实验型** — newest structure, widest gap, for a small A/B

**No cluster may be empty.** If nothing fits a type as its best fit, pull the fallback from the most crowded cluster: move the candidate whose second-best fit is the empty type, not an arbitrary reassignment. Its score and risk columns in Output ② will read lower than the other clusters' winners, and that visible gap is the signal — no prose flags it there; ③ is where the fallback gets named plainly, per its own instructions below.

Within each cluster, sort by score and apply the one promotion gate before the top row is settled: **高风险 cannot win 综合型.** If the highest-scoring candidate in the 综合型 cluster is 高风险, skip it for the top row and promote the next-highest-scoring 低/中风险 candidate in that cluster instead. The other four types carry no such restriction — 传播型 in particular is often the higher-risk pick by nature, and that is expected, not a defect.

If the brief was thin (Step 1 flagged a bare topic, or more than half the brief is 缺), ship the conservative set and **state explicitly what was missing and how it capped the strength** — do not close the gap with invention.

### Step 10 — Build 主标题｜副标题 pairs (`--subtitle on`)

If `--subtitle off`, skip Step 10 and continue to Step 11.

Pair cluster winners (the top row of any table from Step 9) into 主标题 + 副标题, split by `｜`: 主标题 carries the emotion or the reversal, 副标题 delivers the concrete payoff — 《真正厉害的人都学会了反内耗｜3个方法，停止精神内耗》（25 字）.

**The 20–26 budget applies to the combined string, separator included**, because that whole string is what publishes as the title. In practice that leaves roughly 12 characters a side, so a pair is only worth building when both halves are genuinely short — a 24-character 主标题 has no room for a 副标题 and should ship on its own. Build 2–3 pairs, not more.

### Step 11 — Render the result per the Output section

---

## Output

All reader-facing labels, titles, and rationale are written in Chinese; the finished titles are 公众号 copy.

### ① 内容简析

5–8 lines: 核心对象、**人群行为标签**、反常识点、读者回报、证据资产、情绪基调与时效等级、事实边界与合规边界. Mark 缺 fields as 缺. With `--mode rewrite`, precede it with the Step 3 diagnosis and the 保留资产 list.

### ② 候选标题矩阵（单表五组，组内评分从高到低）

One table, all candidates. Group order is fixed: 综合型 → 稳健型 → 传播型 → 搜索型 → 实验型; within each group, sorted by 评分 high to low. **`#` runs continuously down the whole table**, so a candidate can be referenced by number alone in ③.

| # | 候选标题 | 公式 | 心理机制 + 点击钩子 | 评分 | 风险 |
|---|---|-----|---|---:|---|

候选标题 is `{候选标题}（{字数} 字，{角色}）` — the title followed by its character count and which of the five types (综合型/稳健型/传播型/搜索型/实验型) it was classified into at Step 9, so the group boundary reads directly off the title cell. 公式 uses the standard formula names from `references/title-formulas.md`; a stacked pair is `公式A+公式B`. 心理机制 + 点击钩子 is `{心理机制}：{理由}` — the mechanism name, then a specific, technique-naming reason the reader clicks — name the actual mechanic (a number contrast, a rhetorical question, an immersive real-experience frame, a withheld detail), never a restatement of the mechanism itself — e.g. `好奇：反问制造好奇缺口`. 风险 holds only 高 / 中 / 低 — no explanation, no reason, nothing else in that column. No prose commentary beyond the table — the score and risk columns carry the judgment.

### ③ Top 5 一览

Five entries, numbered 1–5, in fixed order (综合型 → 稳健型 → 传播型 → 搜索型 → 实验型), each referencing its cluster's `#1` from ② by number rather than repeating the full row:

```markdown
1. **{角色}**：#{编号} `{候选标题}`
    {一句理由}
```

The one-sentence reason names why this candidate won its cluster; for a weak cluster (Step 9's no-empty-cluster fallback), say so plainly instead of overselling it. This is the only place in the output that carries prose reasoning — ② stays table-only.

### ④ 双标题组合（`--subtitle on`）

| 主标题（字数） | 副标题 | 合计字数 | 主标题抓的情绪 | 副标题给的价值 |
|---|---|---:|---|---|

### ⑤ A/B 测试建议

2–3 groups, each changing **exactly one variable**: 有数字 vs 无数字 / 问句 vs 判断句 / 人群前置 vs 结果前置 / 实体前置 vs 结果前置 / 克制词 vs 强张力词. Keep publish time and cover style constant across each pair, or the variable is not alone.

Prefer pairs drawn straight from ②'s survivors when a clean single-variable pair already exists there. When it doesn't — common at a small `--count` — mint a fresh minimal-pair variant for this section alone, but gate it through `scripts/script.py` before presenting it, exactly like any other candidate; nothing with a character count in this output ships ungated.

```markdown
**第{N}组：{变量A名称} vs {变量B名称}**

- A {变量A名称}：`{候选标题A}`
- B {变量B名称}：`{候选标题B}`
- 点评：{一两句话说清两个版本各自更适合的读者群体或分发场景}
```

### ⑥ 流程审计

| 步骤 | 执行摘要 |
|---|---|

One row per workflow step, 1 through 11, including Step 8's four numbered sub-steps (草稿 / 加料与叠公式 / 去 AI 味核查 / 单条过闸) as their own rows after the Step 8 row. 步骤 names the step as `{N}[.{M}] {短名}` — give the short name enough room to read in full on one line rather than compressing it to the point of wrapping (e.g. `8.3 单条过闸`, not a shorter abbreviation that loses the meaning). 执行摘要 states concretely what happened this run — counts, selections, key numbers, not a restatement of the step's own instructions — then ends with whether any of the workflow's built-in conditionals fired this run (a floor or cap reached, a skip, best-of-3, the no-empty-cluster fallback, the 高风险 promotion gate), e.g. `...；触发：多样性上限` or `...；无特殊规则触发` when nothing unusual happened. This section is a self-audit of the run, not a restatement of ① or ②.

---

## Gotchas

- **20–26 is a hard gate, not a target.** The script eliminates anything outside it. 19 characters is not "close enough" and 27 is not "slightly long" — regenerate rather than trimming a character off a word that was carrying meaning.
- **A padded 26 is worse than an honest 22.** Length is only earned by filled slots. Adjectives added to reach the floor are exactly the AI tell this skill exists to remove.
- **A bare demographic label reads as AI even when everything else is right.** 宝妈、职场人、年轻人、普通人 alone are the tell, and the fix is a behavior, never a stronger adjective. The one exception is 情绪共鸣型, which is built on the group's own pre-existing self-label (80 后、成年人) — there the bare label is the formula, so cite it and keep it. A label the article just coined does not qualify; anchor it with a behavior instead, same as everywhere else.
- **Numbers are not automatically strong.** Only about 30% of 10万+ titles carry one, while about 66% carry a concrete entity. Anchor an entity first; reach for a number only when the gap between two of them does the work (`从月薪3千到月入5万`).
- **公众号 has almost no search long tail.** Unlike 小红书, a 公众号 title lives or dies on first-send and forwarding, so emotion and conflict outrank keyword coverage — but keep the core entity intact for 搜一搜.
- **emoji are a restraint item here**, 0–1 at most. What reads as native on 小红书 reads as cheap in a 公众号 subscription list.
- **热点 titles expire, the 观点 half does not.** In `热点 + 观点` the colon is the dividing line: the first half borrows traffic, the second half is the part worth being remembered for. Never borrow from 灾难 or 公共安全 events.
- **A single trigger scoring well everywhere can still dominate the tactic list.** Selecting several triggers into the Step 4 pool does not by itself guarantee they all survive into the final manifest — pure score-sum ranking could let the highest one fill most of it. Step 6's cap (`⌊--count × 0.3⌋` per formula and per trigger, minimum 1) bounds this while the tactic list is built.
- **A candidate that still fails a check after 3 attempts ships as its best-of-3, flagged.** Neither Step 8 sub-step retries forever — say exactly which gate or de-AI rule it still fails rather than let a residual issue pass silently into scoring.
- **评分 only orders candidates within their own table.** 传播型's `#1` can outscore 综合型's `#1` and that is not a defect — the five tables answer five different questions, and a type's winner is whichever candidate fits that type best, not whichever candidate has the highest score anywhere in the whole pool.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only, no third-party packages.
