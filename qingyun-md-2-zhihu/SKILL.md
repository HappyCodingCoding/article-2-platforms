---
name: qingyun-md-2-zhihu
description: Publishes a Markdown article to the draft box of a Zhihu column (知乎专栏) using the user's already-logged-in Chrome browser. Handles three source shapes — a local .md file, a Notion page link, or another online markdown link — downloads any images to disk (immediately, before Notion's signed image URLs expire), replaces them with placeholders so Zhihu's own broken auto-reupload never triggers, imports the markdown into the Zhihu editor, fills in the title, then inserts every image at its correct position and verifies none are missing. Stops at the draft stage — never publishes. Triggers on "发到知乎", "知乎草稿", "md-2-zhihu", "publish to zhihu", or a Zhihu draft-box request paired with a markdown/Notion source.
---

# Markdown → Zhihu Draft

Takes one Markdown article — local file, Notion page, or another online link — and lands it in the user's Zhihu column draft box (草稿箱) with the title set and every image correctly placed, ready for the user to review and publish themselves.

## Usage

Callable by explicit options or by natural language (infer `--source` from whatever path/link the user pastes). Name any inferred option before running. If the source type is ambiguous (e.g. a bare string that could be a path or a broken URL), ask rather than guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `--source` | option (required) | local file path / Notion page URL / other online markdown URL | — | The article's source. Type is inferred: a path that exists on disk is local; a URL containing `notion.so` or `app.notion.com` is a Notion page; any other URL is fetched generically. |
| `--title` | option | any string | inferred from the source's first heading | Overrides auto-detected title. When inferred, the heading is also stripped from the body so it isn't shown twice (once as the Zhihu title field, once again as the first line of the article). When `--title` is given explicitly, the body is left untouched. **Required for a Notion source** — Notion keeps the page title in `properties.title`, outside the body, so there is no heading to infer from and the script aborts rather than importing an untitled draft. |

## Workflow

### Step 1 — Resolve `--source` and `--title`

Classify `--source` (local path / Notion link / other online link) and state the classification before proceeding. If `--title` wasn't given, say where the title will come from: the source's first heading for a local file or an online markdown link, or `properties.title` for a Notion page, which Step 2 lifts out separately.

### Step 2 — Get the article onto local disk

- **Local path**: nothing to do, go to Step 3.
- **Notion link**: load the Notion fetch tool (`ToolSearch` for `notion-fetch`) and call it on the URL. Write the `<content>` block to a local `.md` file (scratchpad directory), and note the page's `properties.title` — Notion returns the title there, **not** inside `<content>`, so it has to be passed to Step 3 as `--title`. **Do not do anything else — including opening the browser — between this step and Step 3.** Notion's image links are presigned and expire in roughly 5 minutes; Step 3 downloads every image immediately, so the two steps must run back to back in the same turn.
- **Other online link**: fetch the content directly (`WebFetch` or a direct download) and save it to a local `.md` file the same way.

**This file is raw input for the script, not a document.** Nothing reads it but Step 3, which is the only thing in this skill that decides markdown formatting — block separation, indentation, lists and tables are all its job, and it does them the same way every run. Your job here is a byte-for-byte transfer and nothing else. Go straight from writing the file to running Step 3 on it.

**Copy the content out character for character.** The article's text passes through your own output on its way to disk, which is the one place in this skill where the author's words can be altered, and every alteration is invisible from here on. Specifically: do not add or remove blank lines — **not even around images, and not "just where it obviously needs one"** — do not change quote characters (`“ ”` are not `"`), do not drop or rewrite inline links, do not unescape anything, do not "tidy" indentation, and do not reformat tables — Step 3 converts raw `<table>` HTML to a pipe table itself, which is what gives Zhihu a real header row. **Do not repair the markdown either** — Step 3's script normalizes block separation, indentation and lists deterministically, and it can only do that correctly if what reaches it is what the source actually said. The title is the single exception: it is lifted out separately, as `--title`.

### Step 3 — Process the markdown (script)

Run:
```
python3 qingyun-md-2-zhihu/scripts/script.py --source <local-md-path> [--title "<title>"]
```
For a Notion source, `--title` is required, not optional — the page title never appears in the body, and the script aborts rather than importing an untitled draft.
This normalizes block separation (see below), extracts the title (or uses `--title`), flattens every list so each item is a single block (see below), downloads every remote image / copies every local image referenced in the markdown, replaces each image with a plain-text placeholder (`【ZHIHU-IMG-N】`) on its own paragraph, and prints a JSON manifest: `title`, `processed_markdown` (path), `images_dir`, `images[]` (each with `index`, `placeholder`, `local_path`, in document order), `blank_lines_inserted`, `soft_wrapped_lines`, `expected_structure`, `warnings[]`, and `errors[]`.

**Why block separation is normalized.** Markdown starts a new block on a *blank* line; a single newline is only a soft wrap. `notion-fetch` returns one block per line with no blank lines at all, and imported that way every consecutive paragraph fuses into one, a paragraph next to a list is swallowed into the list item above it, and a list beginning `1.` silently continues the previous list instead of starting its own. The script decides per adjacent pair rather than per file, so a source that has blank lines in some places and not others — around its images but not its paragraphs, say — is repaired everywhere it needs to be. A file that is already well-formed has no adjacent block lines to act on and comes through byte-identical. Where two paragraph lines meet, the line above is what decides: ending on sentence-final punctuation means two blocks, breaking mid-sentence means one soft-wrapped block, counted in `soft_wrapped_lines`.

**Why lists get flattened.** Zhihu's editor is Draft.js: its content is a flat run of blocks, with no `<ol start>` and no way to nest a block inside a list item. Any block that interrupts a run of list items — nested bullets, a sub-paragraph, a code block — closes the list, and the items after it open a **new** list that restarts at 1. The script therefore folds each item's nested content into the item itself using markdown hard breaks, which survive the import as line breaks inside that one item. Nested markers are demoted (`- ` → `• `, `1. ` → `1）`) so they aren't re-parsed as a nested list.

If `errors` is non-empty, stop and report exactly which images failed to download before continuing — a silently-dropped image is not acceptable. If `warnings` is non-empty, relay them: they name list content the script could not flatten, so that list will still break where the warning says.

### Step 4 — Load the browser tools and open the Zhihu editor

Load the needed Claude-in-Chrome tools in one `ToolSearch` call (`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__form_input`) if they aren't already loaded. `read_network_requests` is there for diagnosing a stalled image upload in Step 8; loading it up front avoids a `ToolSearch` detour mid-insert. Note the server prefix is `mcp__claude-in-chrome__` throughout — a similarly named browser server may also be connected, and its tools act on a different browser.

Use the **user's own connected Chrome** (Claude in Chrome) — never launch a separate browser instance with a debug port. Get the tab context, reuse an existing `zhuanlan.zhihu.com` tab if one is open, otherwise navigate a tab to `https://zhuanlan.zhihu.com/write`.

If the page shows a login wall instead of the editor, stop and use `AskUserQuestion` to ask the user to log into their Zhihu account in that browser, then re-check.

### Step 5 — Import the processed markdown

Click 导入 in the toolbar, then the 导入文档 MD/Doc menu item. A dialog opens on a 导入文档 / 导入链接 tab pair; make sure 导入文档 is the active tab, then find its file input with the tagging trick below and set it to the manifest's `processed_markdown`. **Do not click the input itself**; clicking opens a native file dialog that automation cannot drive.

**Targeting a file input.** The page carries several `<input type="file">`, and more than one matches any loose description — the attachment input accepts `.md` too, so "the markdown input" is ambiguous to a description-based search and picking the wrong one fails in ways that look like success. `find` and `read_page` match on description, not attributes, so select in page JS by the `accept` string and hand the result a label to search for:

```js
const input = Array.from(document.querySelectorAll('input[type=file]'))
  .find(el => el.accept.includes('.markdown'));   // the MD/Doc import input
input.setAttribute('aria-label', 'ZHIHU-TARGET-INPUT');
input.accept;   // print it and confirm before uploading
```

Then `find` `ZHIHU-TARGET-INPUT` and upload to that ref. Always print the chosen `accept` and check it before uploading — that one line is what separates the right input from a silent misfire.

Wait for the conversion to finish and the editor body to populate. The URL changes to `/p/<article-id>/edit` — record that id, Step 9 needs it. See `references/zhihu-editor-notes.md` for the underlying `document/convert` call.

### Step 6 — Set the title

Put the manifest's `title` into `textarea[placeholder*="请输入标题"]`. Zhihu never derives the title from imported content, so this step is required even though Step 5 populated the body. It is a React-controlled input, so a plain `value =` assignment is ignored — either type into it, or use the native setter followed by an `input` event.

Then read the field back and confirm it equals the manifest's `title`. An empty title field is invisible in a body-focused screenshot, and the draft still looks complete.

### Step 7 — Verify the imported body against the manifest, before touching images

Zhihu's converter can merge, split or swallow blocks in ways that still read plausibly on screen, so check the structure it actually built against the structure the script said to expect — not against your memory of the article. Read both:

```js
const ed = document.querySelector('.public-DraftEditor-content');
const top = Array.from(ed.children[0].children);
({
  paragraphs: top.filter(n => n.tagName === 'DIV').length,
  blockquotes: top.filter(n => n.tagName === 'BLOCKQUOTE').length,
  lists: top.filter(n => n.tagName === 'OL' || n.tagName === 'UL')
            .map(n => ({type: n.tagName.toLowerCase(), items: n.children.length})),
  tables: Array.from(ed.querySelectorAll('table'))
            .map(t => ({rows: t.querySelectorAll('tr').length})),
  placeholders: (ed.innerText.match(/ZHIHU-IMG-\d+/g) || []).length
})
```

Against the manifest's `expected_structure`, every one of these must hold:

| Check | Requirement | What a mismatch means |
|---|---|---|
| `lists` | identical, in order — same count, same types, same item counts | items fused into one list, or one list split into several that renumber from 1 |
| `tables` | same row counts | the table was mangled or partly absorbed |
| `blockquotes` | same count | adjacent quotes merged, or a paragraph was absorbed into one |
| `placeholders` | equals `expected_structure.images` | an image position was lost |
| `paragraphs` | **at least** `expected_structure.paragraphs` | fewer means paragraphs merged or got swallowed into a neighbouring block. (More is fine — Draft.js keeps a trailing empty block, and it wraps some blocks in an extra `div`.) |

Also confirm every placeholder (`【ZHIHU-IMG-1】` … `【ZHIHU-IMG-N】`) is present in order, and that no raw image markdown or URL leaked through unconverted.

**What this check cannot see.** `expected_structure` is computed from the processed markdown, so it proves Zhihu imported the script's output faithfully — not that the article reaching the script was intact. If Step 2 lost blank lines, the manifest and the editor agree on a paragraph count that is simply too low, and every row above passes. So before trusting it, sanity-check the manifest itself against the article you fetched: `expected_structure.paragraphs` should be in the range the source's own paragraphs suggest, and a non-empty `soft_wrapped_lines` on a source that isn't hard-wrapped prose means paragraphs arrived already joined. Relay any `warnings[]` rather than reading past them.

**On any mismatch, stop and report the two structures side by side.** Do not hand-patch the editor to make the numbers agree — the content has to be right in the markdown handed to the importer, so the fix belongs in Step 2 (something was altered on the way to disk) or in the script. Never skip ahead to image insertion with a mismatch outstanding: images are placed by finding placeholders, and a mangled body puts them in the wrong place.

### Step 8 — Insert every image, in order

Zhihu's image dialog uploads the file first and inserts it on a second, explicit action — **the insert only happens when you click 插入图片**, and it lands at wherever the editor's cursor was. Both halves matter: skipping the button silently discards the upload, and an unset cursor puts the image in the wrong place.

**First, resolve the image input once.** Click the 图片 toolbar button with the cursor anywhere, and identify the dialog's file input by its `accept` using the tagging trick from Step 5 — the image input's `accept` starts with `image/webp,image/jpg,image/jpeg,image/png`. There is no input whose `accept` is `image/*`; the one that *looks* right to a description-based search is usually the 附件 input, which accepts `.png`/`.jpg` among a list of document types and inserts a file-name card instead of a picture. Print the chosen `accept` and confirm it before going further, then press Escape — nothing was uploaded yet, so nothing is lost. The same input is reused each time the dialog reopens, so this resolution holds for the whole loop, and the risky part is now behind you before any placeholder gets deleted.

Then, for each image in the manifest, **in order, one at a time**:

1. **Select the placeholder, and record its neighbours.** In page JS, walk the editor's text nodes for `【ZHIHU-IMG-N】`, and before touching anything record the text of the top-level block before it and after it — those two strings are the anchor that proves, later, that the image landed where the placeholder was. Then scroll it to mid-viewport (`window.scrollBy(0, rect.y - 400)`), read its `getBoundingClientRect()`, convert to click coordinates (see note below), and triple-click it. Confirm `window.getSelection().toString()` contains `ZHIHU-IMG-N` before going on; abort this image if it doesn't. Draft.js only honours a selection made by real input — a `Range` set programmatically is ignored.
2. **Clear it.** Press Backspace so the placeholder is gone and the cursor sits in the now-empty paragraph. That cursor is where the image will land. From here until the insert lands, the anchor exists only in what you recorded in step 1.
3. **Open the dialog.** Click the 图片 toolbar button, and use the input resolved above.
4. **Upload.** Set that input to the image's `local_path` with the file-upload tool, then wait for the dialog footer to read 已上传 N 张图片. **The tool fires the input's change handler itself**, and the dialog can take several seconds to catch up. Do not help it along by dispatching a `change` or `input` event in page JS — the handler then runs twice and inserts the image twice. If the footer hasn't updated, wait longer and read it again.
5. **Insert.** Click 插入图片. The dialog closes and the image appears at the cursor. Its `src` may briefly be a `blob:` URL rather than `https://pic…` — the upload is usually finished by now but not always, so poll the `src` until it becomes a `pic…` URL before moving on. If the block turns into 上传失败 instead, click its **重试** button; that recovers it in place, and only if retrying fails is the image genuinely lost.
6. **Confirm it landed in the right place**, not merely that it landed:

```js
const ed = document.querySelector('.public-DraftEditor-content');
const top = Array.from(ed.children[0].children);
const img = ed.querySelectorAll('img')[/* the one just added */];
const block = top.find(n => n.contains(img));
const i = top.indexOf(block);
({ imgCount: ed.querySelectorAll('img').length,
   src: img.src.slice(0, 40),
   prev: (top[i-1]?.innerText || '').slice(0, 30),
   next: (top[i+1]?.innerText || '').slice(0, 30) })
```

`prev` and `next` must match what step 1 recorded, and `imgCount` must be exactly one higher than before. A count that rose while the neighbours changed means the image went in at a stale cursor — which is precisely what a count-only check cannot see.

**When the check fails, what to do depends on how it failed.** Two of these are repairable in place; only the last needs a rebuild.

| Symptom | Fix |
|---|---|
| `imgCount` rose by two — the same image inserted twice | Hover the extra figure and click its **×** delete control, then re-run the check. The surviving image is normally in the right place; the recorded neighbours will confirm it. Caused by dispatching an upload event by hand — don't. |
| The block reads 上传失败 | Click **重试** on that block. It uploads in place and keeps its position. |
| The image sits between the wrong neighbours, or went in as a file-name card | **Rebuild.** Its placeholder was consumed in step 2, so there is no anchor left to retry against, and an undo restores the text without restoring the cursor. Clear the body, re-import from Step 5, and start the loop again with the input already resolved. |

Do not carry on inserting the remaining images into a draft that is already wrong — but equally, do not rebuild a draft whose only problem is a duplicate you can delete.

**Note — click coordinates.** The click coordinate frame can differ from the page's CSS viewport; multiply JS coordinates by `frameWidth / window.innerWidth` (the screenshot result reports the frame; `innerWidth`/`innerHeight` come from the page). Skipping this lands clicks a few percent off, silently.

### Step 9 — Verify against the server, not just the screen

The editor's DOM can be ahead of what Zhihu has actually stored, and autosave lags (it can sit on 草稿保存中 for minutes). Check the saved copy:

```
GET /api/articles/<article-id>/draft   (same-origin, credentials included)
```

Confirm in the **returned content**: `<img` count equals the manifest count, every one has an `https://pic…` src, no `ZHIHU-IMG` placeholder remains, and `state` is `draft`. If the server copy lags, force a flush by navigating to the same edit URL again (`force: true` — the "Leave site?" prompt is expected), then re-check. Only report success on the server-side copy.

Then check the images are in the right **places**, which a count cannot tell you. Parse the returned HTML, list its block-level children in order, and confirm each `<img>` sits between the same two pieces of text it sits between in the processed markdown — image N should follow the paragraph that precedes `【ZHIHU-IMG-N】` in `processed_markdown` and precede the one that follows it. Report the first mismatch with both orderings rather than a summary; an image in the wrong position is invisible in every count-based check and in a screenshot of any other part of the article.

### Step 10 — Hand off to the user

Report back: the draft URL (`zhuanlan.zhihu.com/p/<id>`), the title used, and the image count, with a screenshot of the finished draft. **Never click 发布 (publish)** — the article stays in the draft box for the user to review and publish themselves.

## Output

A short report to the user: draft URL, title, number of images placed, and a screenshot of the finished draft — nothing else changes on their account.

## Gotchas

- **Zhihu's own "reupload from markdown" step is broken for local images and will fail every time** (`400 图片地址不合法`) — this is exactly why Step 3 replaces images with placeholders before import instead of letting Zhihu try to fetch them itself. See `references/zhihu-editor-notes.md`.
- **A single newline is not a paragraph break.** Markdown starts a new block only on a *blank* line, and `notion-fetch` returns one block per line with none. Left uncorrected this fuses consecutive paragraphs, absorbs a paragraph next to a list into the item above it, merges adjacent blockquotes, and makes a `1.` list continue the previous list rather than start its own — all of it looking like a plausible article on screen. Step 3 normalizes this; Step 7 catches whatever it missed.
- **Anything you retype can be altered without you noticing.** The Notion path routes the article through your own output on the way to disk. Observed drift from real runs: 40 blank lines dropped, the title lost, 20 curly quotes flattened to straight ones, two inline links silently removed — and, in another run, blank lines added around the images but not between the paragraphs, which merged every paragraph run in the finished draft. Improving the formatting is as damaging as degrading it; Step 3 is the only thing that decides format.
- **The manifest is not independent evidence of the input.** `expected_structure` is derived from the processed markdown, so a source that arrived already merged produces a manifest and an editor that agree with each other and disagree with the article. Step 7 catches Zhihu mangling the import; only reading the manifest against the source catches Step 2 mangling the article.
- **Draft.js restarts ordered-list numbering at every interruption.** There is no `<ol start>` in Zhihu's editor, and a list item cannot contain a nested block. Any block between two items — nested bullets, a sub-paragraph, an image — ends the list, and the following items render as 1, 2, 3 again no matter what the source markdown said. Step 3's flattening pass exists for this; Step 7 verifies it held. Tab-indented lines are a related hazard: outside a list a tab-indented line imports as a `<pre>` code block.
- **Notion image links expire in ~5 minutes.** Steps 2 and 3 must run back to back with nothing else in between when the source is a Notion page.
- **Uploading is not inserting.** The image dialog uploads on file-select but only places the image when 插入图片 is clicked. Dismissing the dialog after upload (Escape, clicking away) throws the insertion away and leaves no error — it just looks like nothing happened.
- **Several file inputs match any loose description, and the wrong one fails like a success.** No input has `accept="image/*"`; the image dialog's starts `image/webp,image/jpg,image/jpeg,image/png`, while the 附件 input accepts `.png`/`.jpg` alongside `.pdf`/`.md`/`.doc` and the article-cover input accepts `.jpeg, .jpg, .png`. Uploading an image to the attachment input turns the dialog button into 添加文件 and inserts a file-name card, not a picture. Select by `accept` in page JS and print it before uploading; `find` matches descriptions, not attributes.
- **A count going up is not the image being in the right place.** The insert lands wherever the cursor happens to be, so a stale cursor produces a draft with the right number of images, all with valid CDN URLs, no placeholders left — and a picture several paragraphs from where it belongs. Only a neighbour check catches it, which is why Steps 8 and 9 record and compare the surrounding text.
- **Never judge an inserted image by what it depicts.** An article about a codebase legitimately contains screenshots of folder trees, editors, and terminals that can look like stray UI from your own environment. Verify by dimensions against the local file (`sips -g pixelWidth -g pixelHeight`), or open the local file and look — never by assuming what the picture "should" show.
- **Click coordinates may not equal page coordinates** — scale by `frameWidth / window.innerWidth` (Step 8's click-coordinates note). A silently mis-landed click is easy to mistake for a broken editor.
- **A freshly loaded `/edit` page can render content while still ignoring all keyboard input.** If typing has no effect, the app has not finished booting (the tab title is still `知乎 - 知乎` rather than `写文章 - 知乎`) — wait or reload rather than concluding the editor is read-only.
- **An image block is atomic: Backspace/Delete will not remove it, but the UI will.** Hovering a figure reveals a **×** control that deletes it, and a block showing 上传失败 carries a **重试** button that re-uploads it in place. Reach for those before rebuilding the draft — an image that failed or got inserted twice is repairable, and only a wrongly-positioned one is not.
- **Inserting through the dialog does not guarantee the image is already on the CDN.** The block can appear with a `blob:` src and finish uploading afterwards, or fail outright with 上传失败. Poll the `src` until it is a `pic…` URL rather than assuming step 4 finished the job.
- **Never dispatch a `change` or `input` event on a file input yourself.** The file-upload tool already fires the handler; a second, hand-made event runs it twice and inserts the image twice. The dialog is simply slow — wait and re-read it.
- **The title is never auto-filled** — always do Step 6 explicitly, even though the body already looks complete after Step 5. Read the field back afterwards: a draft that reaches the draft box with an empty title looks finished in the editor and is not.
- **This skill only ever produces a draft.** It does not click 发布 under any circumstance, regardless of how the request is phrased.
- If Zhihu shows a captcha/risk-control challenge mid-flow, stop and ask the user to complete it manually in the browser rather than trying to click through it.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only (`certifi` is used for TLS if present, but is not required).
- A Chrome browser connected via Claude in Chrome, with the user already logged into Zhihu. Steps 7–9 need page-JS execution, so the browser tooling must include a JavaScript-evaluation capability.
- For Notion sources, a connected Notion tool (`notion-fetch`) in this session.
