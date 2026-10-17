# 一键排版 templates

The templates the card editor offers after 一键排版, in the order the panel
lists them, read from the panel on 2026-10-17. Step 5.1 of SKILL.md shows this
list to the user, and uses the **Suits** column when the agent picks a
template for the copy.

**Backgrounds** are the template's colour swatches, in panel order; swatch 1
is what a template starts with when it is selected. A swatch sets the card
background, and the template derives its text and accent colours from it, so
the finished background can differ slightly from the swatch's hex.

| # | Template | Backgrounds | Look | Suits |
|---|---|---|---|---|
| 1 | 轻感明快 | `#313131` charcoal · `#3194E5` blue · `#F07F34` orange · `#FFFFAA` pale yellow · `#F9F9F9` off-white · `#CE8D38` ochre · `#FFCEEB` pink · `#83F7C8` mint | Solid colour ground, big bold coloured headline, quote mark | Short, punchy notes: tips, opinions, one-line hooks |
| 2 | 清晰明朗 | `#F5F5F5` light grey · `#FBEAD4` cream · `#121212` black | Serif headline over an architectural photo block, thin rules | Business, career and reflective long reads |
| 3 | 优雅几何 | `#FFEF9D` yellow · `#A4E2FF` sky · `#81EB98` green · `#B3FFC4` pale green · `#6FC8FC` blue · `#FDCE6D` amber | Bold headline on a photo, chapter labels, clean geometry | Knowledge and science explainers with sections |
| 4 | 线条复古 | `#E9F592` lime · `#DDECFF` pale blue · `#FFEEA4` butter | Highlighter headline, numbered grid, retro line work | Design, lifestyle and product round-ups |
| 5 | 涂鸦马克 | `#FFEA7F` yellow · `#FFCFF3` pink · `#BFEEFF` light blue | Hand-drawn doodles and marker title | Parenting, casual and warm personal notes |
| 6 | 手帐书写 | `#FFEDA8` yellow · `#F2B0BB` rose · `#D0DEF8` periwinkle · `#CCF1C7` mint | Scrapbook journal: paper, tape, stamps, photos | Travel diaries, itineraries, life logs |
| 7 | 理性现代 | `#0876EF` blue · `#B0160C` red · `#A3722C` bronze | Heavy sans headline, accent bar, photo band | Analysis, tech, finance, serious commentary |
| 8 | 文艺清新 | `#F6C0D7` pink · `#AAC7E2` blue · `#B7DEBE` sage · `#EDD9C5` sand | Soft pastel, serif title, dotted chapter list | Essays, nature, gentle literary pieces |
| 9 | 简约基础 | `#F9F9F9` off-white · `#DDF5DE` mint · `#F6F6F6` light grey · `#FFFEEA` ivory · `#E9E9E9` grey · `#3A3A3A` charcoal | Plain, large black headline, body text only | Anything text-heavy; the neutral default |
| 10 | 素雅底纹 | `#AAC7E2` blue · `#F6C0D7` pink · `#B7DEBE` sage · `#EDD9C5` sand | Subtle patterned paper, blue serif title | Quiet essays, reading notes, reflections |
| 11 | 灵感备忘 | `#2E2E2E` dark · `#4BA1FF` blue · `#F4F4F4` light | iPhone 备忘录 (Notes app) screen with yellow accents | Personal experience posts, how-tos, guides told first-hand |
| 12 | 杂志先锋 | `#00E180` green · `#40C7FF` cyan · `#CBEBEA` aqua · `#DCF07F` lime | Magazine layout, bold title, coloured chapter tabs | Brand, luxury, culture and design features |
| 13 | 黄昏手稿 | `#BDA875` khaki · `#E9B2B2` blush · `#FFE8C7` peach · `#7A8CCA` dusk blue | Antique manuscript, classical serif, ornaments | Fiction, history, classical and poetic writing |
| 14 | 逻辑结构 | `#B0160C` red · `#A3722C` bronze · `#0876EF` blue | Structured headings, red accent bars, dense body | Reports, AI/tech trends, frameworks |
| 15 | 黑白极简 | `#FBEAD4` cream · `#F5F5F5` light grey · `#121212` black | Minimal, red-brown serif headline, generous space | Business insight, essays that need a calm look |
| 16 | 大图纯享 | `#F3DFB0` wheat · `#282828` charcoal · `#555555` grey | Full-bleed image cover, text pages after | Stories and notes led by a strong image |
| 17 | 拼接色块 | `#E9F592` lime · `#DDECFF` pale blue · `#FFEEA4` butter | Colour-block highlighted title, bold sans | City, space and lifestyle features |
| 18 | 平实叙事 | `#FDCE6D` amber · `#FFEF9D` yellow · `#6FC8FC` blue · `#81EB98` green · `#A4E2FF` sky · `#B3FFC4` pale green | Dark ground, bold yellow-white title, photo | Money, career and practical advice |
| 19 | 札记集尘 | `#3A3A3A` charcoal · `#74A3D1` steel blue · `#88181E` maroon · `#D0D89E` olive · `#EAEAEA` light grey | Vertical Chinese typesetting, literary | Chinese literary prose, poetry, classical tone |
| 20 | 交叉拓扑 | `#40C7FF` cyan · `#00E180` green · `#DCF07F` lime · `#CBEBEA` aqua | Strong colour blocks, big black title | Bold statements, trend and concept pieces |

## Reading the live list

The panel is in the card editor only. Before applying a choice, read the live
list and check the chosen template and swatch are on it; when XHS has added,
removed or renamed templates, show the user the live list instead of this one.

```js
(() => JSON.stringify([...document.querySelectorAll('.template-list .template-card')].map(card => ({
  name: card.querySelector('.template-title').textContent.trim(),
  selected: card.classList.contains('selected'),
  backgrounds: [...card.querySelectorAll('.color-item')].map(i => ({
    hex: i.style.getPropertyValue('--item-color').trim().toUpperCase(),
    active: i.classList.contains('active')
  }))
}))))()
```

The panel renders a moment after the cards: poll until it returns a non-empty
list.
