---
name: qingyun-md-2-zhihu
description: Publishes a Markdown article to the draft box of a Zhihu column (知乎专栏) using the user's already-logged-in Chromium browser (Chrome or Edge) driven through the `bsk` CLI. Handles three source shapes — a local .md file, a Notion page link, or another online markdown link — downloads any images to disk (immediately, before Notion's signed image URLs expire), replaces them with placeholders so Zhihu's own broken auto-reupload never triggers, imports the markdown into the Zhihu editor, fills in the title, then inserts every image at its correct position and verifies none are missing. Stops at the draft stage — never publishes. Triggers on "发到知乎", "知乎草稿", "md-2-zhihu", "publish to zhihu", or a Zhihu draft-box request paired with a markdown/Notion source.
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

### Step 4 — Clear the setup gate, then open the Zhihu editor

The browser is driven through `bsk`, which runs the automation inside an isolated **Agent Window** of the user's own logged-in browser. Three things must be in place before any browser work. Check them in this order and stop at the first failure — each later step is useless without the earlier one.

**1. The `bsk` CLI.** If `bsk --version` fails, install it (no sudo, writes to `~/.local/bin`):

```
curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh     # macOS / Linux
irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex          # Windows
```

**2. The browser extension.** `bsk doctor` exits `0` when everything is connected and `1` otherwise; its `extension connected` line is the one that matters here. It needs no session — any `bsk` command starts the daemon it relies on. If it is not connected, the extension has to be installed from the browser's own store — this cannot be automated, because the store's install confirmation is outside the page and both `bsk` and CDP are blocked from `edge://`/`chrome://` pages. Navigate the browser to the right store URL so the user is one click away, then ask them to add it and confirm before continuing:

- Edge: `https://microsoftedge.microsoft.com/addons/detail/browserskill/emacgiaaaiojkkpkddmmdfhmokgmnikg`
- Chrome and other Chromium browsers: `https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi`

**3. The extension's file-URL permission.** This skill uploads files twice — the markdown in Step 5 and every image in Step 8 — and both fail without it. `bsk doctor` does **not** cover this, so it surfaces only as an upload error reading `Not allowed` with no named cause. Verify it up front rather than discovering it mid-import.

Start the session now — the probe needs one, and the same session carries through the rest of the run:

```
bsk session start
```

It prints a short four-character token (`blfs`, `aykd`, …). That token *is* the value every later `--session` takes; there is nothing to parse out of it.

**Do not pass `--no-focus`.** It leaves the Agent Window hidden, and a hidden tab will not perform the text selection Step 8 depends on.

Then upload a file to a throwaway input on a blank page. Any small local file will do — write one to the scratchpad rather than hunting for a candidate:

```
bsk navigate "https://example.com" --session <id>
bsk evaluate "(()=>{const i=document.createElement('input');i.type='file';i.id='probe';i.style.cssText='position:fixed;top:10px;left:10px;width:220px;height:36px;z-index:9999';document.body.appendChild(i);return 1})()" --session <id>
bsk upload --selector "#probe" --file <any-local-file> --session <id>
bsk evaluate "(()=>document.getElementById('probe').files.length)()" --session <id>
```

A result of `1` means uploads work. `Not allowed`, or `0` files attached, means the permission is off: ask the user to open `edge://extensions/` (or `chrome://extensions/`), find **BrowserSkill**, click **Details**, and turn on **Allow access to file URLs**. Toggling it reloads the extension and kills every open session, so start a fresh session afterwards.

**Clear this whole gate before Step 2 when the source is a Notion page.** Notion's signed image URLs expire in about five minutes, and a setup failure discovered after the fetch burns that window.

With the gate clear, open the editor:

```
bsk navigate "https://zhuanlan.zhihu.com/write" --session <id>
```

The editor renders its content before it accepts input. Poll `document.title` until it contains `写文章` before doing anything else — until then the page looks ready and silently ignores everything.

If the page shows a login wall instead of the editor, stop and use `AskUserQuestion` to ask the user to log into their Zhihu account in that browser, then re-check.

### Step 5 — Import the processed markdown

Click 导入 in the toolbar, then the 导入文档 MD/Doc menu item. A dialog opens on a 导入文档 / 导入链接 tab pair; make sure 导入文档 is the active tab, then set its file input to the manifest's `processed_markdown`. **Do not click the input itself**; clicking opens a native file dialog that automation cannot drive.

**Targeting a file input.** The page carries several `<input type="file">`, and more than one matches any loose description — the attachment input accepts `.md` too, so "the markdown input" is ambiguous and picking the wrong one fails in ways that look like success. Select by the `accept` attribute, which is exact, and tag the winner so the upload can address it. These inputs are `display:none`, and `bsk` refuses to act on an element it cannot see, so the same snippet also makes it visible:

```js
(() => {
  const x = Array.from(document.querySelectorAll('input[type=file]'))
    .find(y => y.accept.includes('.markdown'));       // the MD/Doc import input
  x.setAttribute('data-zhmd', '1');
  x.style.cssText = 'position:fixed;left:10px;top:10px;width:220px;height:36px;opacity:1;z-index:99999;display:block;visibility:visible';
  return x.accept;                                    // print it and confirm before uploading
})()
```

Every `bsk evaluate` snippet must be wrapped in an IIFE like this one. Snippets share a single global scope across calls, so a bare `const x` collides with the next snippet that uses the same name and fails with `Identifier 'x' has already been declared`.

Then upload to the tag:

```
bsk upload --selector "input[data-zhmd='1']" --file <processed_markdown> --session <id>
```

Always print the chosen `accept` and check it before uploading — that one line is what separates the right input from a silent misfire.

Conversion is finished when the URL changes to `/p/<article-id>/edit`; that redirect is the success signal, and the id it carries is what Step 9 needs, so read it from `location.href` and record it. See `references/zhihu-editor-notes.md` for the underlying `document/convert` call.

### Step 6 — Set the title

Put the manifest's `title` into `textarea[placeholder*="请输入标题"]`. Zhihu never derives the title from imported content, so this step is required even though Step 5 populated the body. It is a React-controlled input, so a plain `value =` assignment is ignored — use the native setter followed by an `input` event:

```js
(() => {
  const ta = document.querySelector('textarea[placeholder*="请输入标题"]');
  const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  set.call(ta, '<title>');
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  return 'set';
})()
```

Then read the field back and confirm it equals the manifest's `title`. An empty title field is invisible in a body-focused screenshot, and the draft still looks complete.

### Step 7 — Verify the imported body against the manifest, before touching images

Zhihu's converter can merge, split or swallow blocks in ways that still read plausibly on screen, so check the structure it actually built against the structure the script said to expect — not against your memory of the article. Read both:

```js
(() => {
  const ed = document.querySelector('.public-DraftEditor-content');
  const t = Array.from(ed.children[0].children);
  return JSON.stringify({
    paragraphs: t.filter(n => n.tagName === 'DIV').length,
    blockquotes: t.filter(n => n.tagName === 'BLOCKQUOTE').length,
    lists: t.filter(n => n.tagName === 'OL' || n.tagName === 'UL')
             .map(n => ({type: n.tagName.toLowerCase(), items: n.children.length})),
    tables: Array.from(ed.querySelectorAll('table'))
             .map(x => ({rows: x.querySelectorAll('tr').length})),
    placeholders: (ed.innerText.match(/ZHIHU-IMG-\d+/g) || []).length
  });
})()
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

Each image replaces its own placeholder, one at a time, in manifest order. The image lands wherever the editor's cursor is, so the cursor must be placed deliberately every time.

**First, close the image dialog left open by the previous image.** It does not close itself — expect it to still be there at the top of every iteration, not as an occasional glitch. While it is open it swallows every click that follows, and the symptom — an empty text selection — looks nothing like its cause.

```js
(() => !!document.querySelector('.Modal'))()
```

While that returns `true`, press Escape and check again. One Escape does not always take, so loop a few times rather than pressing once and assuming.

Then, for each image in the manifest, **in order, one at a time**:

1. **Find the placeholder, scroll it into view, and record its neighbours.** Locate the top-level block containing `【ZHIHU-IMG-N】`, call `scrollIntoView({block:'center'})` on it, and record the text of the block before and after it — those two strings are the anchor that proves, later, that the image landed where the placeholder was. Tag the innermost `span` holding the text, not the block: the block spans the full editor width, and a click at its centre can land past the end of a short placeholder.

```js
(() => {
  const ed = document.querySelector('.public-DraftEditor-content');
  const t = Array.from(ed.children[0].children);
  const i = t.findIndex(n => n.innerText.includes('ZHIHU-IMG-N'));
  if (i < 0) return JSON.stringify({err: 'no placeholder'});
  t[i].scrollIntoView({block: 'center'});
  const sp = Array.from(t[i].querySelectorAll('span')).filter(s => s.textContent.includes('ZHIHU-IMG-N'));
  sp[sp.length - 1].setAttribute('data-zhtext', 'N');
  return JSON.stringify({
    prev: (t[i-1]?.innerText || '').replace(/\n/g, '').slice(0, 20),
    next: (t[i+1]?.innerText || '').replace(/\n/g, '').slice(0, 20)
  });
})()
```

2. **Select the placeholder with the keyboard**, then confirm the selection. Click once to place the caret, then `End` followed by `Shift+Home` to select the line:

```
bsk click "[data-zhtext='N']" --session <id>
bsk press End --session <id>
bsk press Home --modifiers shift --session <id>
```

Confirm `window.getSelection().toString()` contains `ZHIHU-IMG-N` before going on, and retry the three commands up to three times if it doesn't. Mouse selection is not an option here: a triple-click only selects when the browser window is the frontmost application, which it is not while automation drives it, whereas keyboard selection works regardless. A `Range` set programmatically is ignored too — Draft.js only honours selections made by real input.

3. **Clear it.** Press Backspace so the placeholder is gone and the cursor sits in the now-empty paragraph. That cursor is where the image will land. From here until the insert lands, the anchor exists only in what you recorded in step 1.

4. **Open the dialog and resolve its file input.** Open it only now, with the cursor already parked by step 3 — a file set while the editor holds no cursor is accepted by the dialog and then goes nowhere. Click the toolbar button in page JS rather than by a snapshot ref; toolbar refs are renumbered every time the dialog opens and closes, so a ref captured on the first image is stale by the second:

```js
(() => {
  Array.from(document.querySelectorAll('button'))
    .find(x => x.innerText.trim().includes('图片')).click();
  return 'opened';
})()
```

Then select the input whose `accept` **starts with** `image/webp,image/jpg,image/jpeg,image/png`, tag it, and make it visible — the same IIFE shape as Step 5. Match on that prefix rather than on `image/*`: several inputs accept images, and the 附件 input takes `.png`/`.jpg` among a list of document types and inserts a file-name card instead of a picture. Print the chosen `accept` and confirm it before uploading.

5. **Upload.** `bsk upload --selector "input[data-zh='img']" --file <local_path> --session <id>`. The image is uploaded and placed at the cursor without any further action. Do not dispatch a `change` or `input` event in page JS to hurry it along — the handler then runs twice and inserts the image twice.

6. **Wait for the image to appear, by counting.** Poll the editor's `img` count until it is one higher than it was before this iteration. Count is the reliable signal: the dialog footer's 已上传 N 张图片 text does not always appear, and a 插入图片 button is not always present. If a 插入图片 button *is* on screen while the count has not risen, clicking it is harmless and completes the insert.

7. **Confirm it landed in the right place**, not merely that it landed:

```js
(() => {
  const ed = document.querySelector('.public-DraftEditor-content');
  const t = Array.from(ed.children[0].children);
  const im = ed.querySelectorAll('img');
  const l = im[im.length - 1];
  const b = t.find(n => n.contains(l));
  const i = t.indexOf(b);
  return JSON.stringify({
    n: im.length,
    src: (l.src || '').slice(0, 34),
    prev: (t[i-1]?.innerText || '').replace(/\n/g, '').slice(0, 20),
    next: (t[i+1]?.innerText || '').replace(/\n/g, '').slice(0, 20)
  });
})()
```

`prev` and `next` must match what step 1 recorded, and `n` must be exactly one higher than before. A count that rose while the neighbours changed means the image went in at a stale cursor — which is precisely what a count-only check cannot see.

Once every image is in, poll all `src` values until none is a `blob:` URL. An image can be placed before its upload finishes, and the draft is not correct until each one is a `zhimg.com` URL. If a block reads 上传失败 instead, click its **重试** button; that recovers it in place, and only if retrying fails is the image genuinely lost.

**When the check fails, what to do depends on how it failed.** Two of these are repairable in place; only the last needs a rebuild.

| Symptom | Fix |
|---|---|
| The count rose by two — the same image inserted twice | Delete the extra figure with its **×** control, then re-run the check. The surviving image is normally in the right place; the recorded neighbours will confirm it. Caused by dispatching an upload event by hand — don't. |
| The block reads 上传失败 | Click **重试** on that block. It uploads in place and keeps its position. |
| The image sits between the wrong neighbours, or went in as a file-name card | **Rebuild.** Its placeholder was consumed in step 3, so there is no anchor left to retry against, and an undo restores the text without restoring the cursor. Clear the body, re-import from Step 5, and start the loop again. |

Do not carry on inserting the remaining images into a draft that is already wrong — but equally, do not rebuild a draft whose only problem is a duplicate you can delete.

**Deleting a figure.** An image block is atomic and Backspace will not remove it. Hovering reveals a **×** control, but hovering and clicking as two separate commands races the control's own visibility. Click it in page JS instead:

```js
(() => {
  const s = document.querySelector('<figure selector>').querySelector('.ZDI--Xmark24');
  const c = s.closest('button') || s.closest('[role=button]') || s.parentElement;
  c.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
  c.click();
  return 'deleted';
})()
```

**Recovering a lost placeholder.** If a placeholder was consumed but its image never landed, the empty block it left behind does not survive a reload — Draft.js collapses it. Recreate the block from the block *below* the gap: place the caret in it, press `Home`, press `Enter` to push it down, then `ArrowUp` into the new empty block. Do not build the block from the line above by pressing `End` then `Enter`: `End` goes to the end of the visual *line*, not the end of the block, so on a wrapped paragraph it splits the text mid-sentence.

### Step 9 — Verify against the server, not just the screen

The editor's DOM can be ahead of what Zhihu has actually stored, and autosave lags (it can sit on 草稿保存中 for minutes). **Do this before stopping the session** — ending it discards anything autosave has not yet flushed, and an image that was visible in the editor is simply gone.

Fetch the saved copy from inside the page, same-origin with credentials:

```js
(() => fetch('/api/articles/<article-id>/draft', {credentials: 'include'})
  .then(r => r.json()).then(d => { window.__v = d; return 1; }))()
```

`bsk evaluate` returns the value of the last expression and does not await promises, so read the result in a second call once it has settled. Confirm in the **returned content**: `<img` count equals the manifest count, none has a `blob:` src, no `ZHIHU-IMG` placeholder remains, and `state` is `draft`. If the server copy still lags, wait and re-read rather than assuming.

Then check the images are in the right **places**, which a count cannot tell you. Parse the returned HTML, list its block-level children in order, and confirm each `<img>` sits between the same two pieces of text it sits between in the processed markdown — image N should follow the paragraph that precedes `【ZHIHU-IMG-N】` in `processed_markdown` and precede the one that follows it. Report the first mismatch with both orderings rather than a summary; an image in the wrong position is invisible in every count-based check and in a screenshot of any other part of the article.

### Step 10 — Hand off to the user

Stop the session — `bsk session stop <id>` — once Step 9 has confirmed the server copy, and stop it on failure paths too rather than leaving it to the idle timeout.

Report back: the draft URL (`zhuanlan.zhihu.com/p/<id>`), the title used, and the image count. **Never click 发布 (publish)** — the article stays in the draft box for the user to review and publish themselves.

## Output

A short report to the user: draft URL, title, and number of images placed — nothing else changes on their account.

## Gotchas

- **Zhihu's own "reupload from markdown" step is broken for local images and will fail every time** (`400 图片地址不合法`) — this is exactly why Step 3 replaces images with placeholders before import instead of letting Zhihu try to fetch them itself. See `references/zhihu-editor-notes.md`.
- **A single newline is not a paragraph break.** Markdown starts a new block only on a *blank* line, and `notion-fetch` returns one block per line with none. Left uncorrected this fuses consecutive paragraphs, absorbs a paragraph next to a list into the item above it, merges adjacent blockquotes, and makes a `1.` list continue the previous list rather than start its own — all of it looking like a plausible article on screen. Step 3 normalizes this; Step 7 catches whatever it missed.
- **Anything you retype can be altered without you noticing.** The Notion path routes the article through your own output on the way to disk. Observed drift from real runs: 40 blank lines dropped, the title lost, 20 curly quotes flattened to straight ones, two inline links silently removed — and, in another run, blank lines added around the images but not between the paragraphs, which merged every paragraph run in the finished draft. Improving the formatting is as damaging as degrading it; Step 3 is the only thing that decides format.
- **The manifest is not independent evidence of the input.** `expected_structure` is derived from the processed markdown, so a source that arrived already merged produces a manifest and an editor that agree with each other and disagree with the article. Step 7 catches Zhihu mangling the import; only reading the manifest against the source catches Step 2 mangling the article.
- **Draft.js restarts ordered-list numbering at every interruption.** There is no `<ol start>` in Zhihu's editor, and a list item cannot contain a nested block. Any block between two items — nested bullets, a sub-paragraph, an image — ends the list, and the following items render as 1, 2, 3 again no matter what the source markdown said. Step 3's flattening pass exists for this; Step 7 verifies it held. Tab-indented lines are a related hazard: outside a list a tab-indented line imports as a `<pre>` code block.
- **Notion image links expire in ~5 minutes.** Steps 2 and 3 must run back to back with nothing else in between when the source is a Notion page.
- **Several file inputs match any loose description, and the wrong one fails like a success.** The image dialog's `accept` starts `image/webp,image/jpg,image/jpeg,image/png`, while the 附件 input accepts `.png`/`.jpg` alongside `.pdf`/`.md`/`.doc`, the article-cover input accepts `.jpeg, .jpg, .png`, and a further input accepts a bare `image/*`. Uploading an image to the attachment input turns the dialog button into 添加文件 and inserts a file-name card, not a picture. Select by matching the `accept` prefix in page JS and print it before uploading.
- **`bsk` will not act on an element it cannot see.** It rejects hidden targets with "element not visible (no content quads…)", and every file input on this page is `display:none`. Make the input visible in the same snippet that tags it.
- **`bsk evaluate` snippets share one global scope.** A bare `const x` in one call collides with the next call that reuses the name, failing with `Identifier 'x' has already been declared`. Wrap every snippet in an IIFE, and return a string — `JSON.stringify` where the value is an object.
- **A count going up is not the image being in the right place.** The insert lands wherever the cursor happens to be, so a stale cursor produces a draft with the right number of images, all with valid CDN URLs, no placeholders left — and a picture several paragraphs from where it belongs. Only a neighbour check catches it, which is why Steps 8 and 9 record and compare the surrounding text.
- **Never judge an inserted image by what it depicts.** An article about a codebase legitimately contains screenshots of folder trees, editors, and terminals that can look like stray UI from your own environment. Verify by dimensions against the local file (`sips -g pixelWidth -g pixelHeight`), or open the local file and look — never by assuming what the picture "should" show.
- **Mouse selection does not work while automation drives the browser.** A triple-click selects text only when the window is the frontmost application (`document.hasFocus()`), and it is not. Keyboard selection — click, `End`, `Shift+Home` — works either way. A hidden window is worse still: with `--no-focus` the tab reports `visibilityState: 'hidden'` and performs no selection at all.
- **The image dialog never closes itself.** After an image goes in, its dialog is still open and eating clicks; the symptom is an empty text selection, which reads like a broken selector rather than a modal in the way. Clear it at the top of every image iteration, and re-check after each Escape — one press does not always take.
- **A file set while the editor holds no cursor goes nowhere.** The dialog accepts the upload, no image appears, no error is raised, and the dialog simply stays open. Place the cursor first, then open the dialog — never the other way round.
- **Ending the session discards unsaved work.** An image visible in the editor but not yet autosaved is lost when the session stops, and the draft comes back without it. Confirm the server copy before stopping.
- **Changing the extension's permissions restarts it** and kills every open session. Start a new one afterwards.
- **A freshly loaded `/edit` page can render content while still ignoring all keyboard input.** If typing has no effect, the app has not finished booting (the tab title is still `知乎 - 知乎` rather than `写文章 - 知乎`) — wait or reload rather than concluding the editor is read-only.
- **An image block is atomic: Backspace/Delete will not remove it, but the UI will.** Hovering a figure reveals a **×** control that deletes it, and a block showing 上传失败 carries a **重试** button that re-uploads it in place. Reach for those before rebuilding the draft — an image that failed or got inserted twice is repairable, and only a wrongly-positioned one is not.
- **Inserting through the dialog does not guarantee the image is already on the CDN.** The block can appear with a `blob:` src and finish uploading afterwards, or fail outright with 上传失败. Poll the `src` until it is a `pic…` URL rather than assuming step 4 finished the job.
- **Never dispatch a `change` or `input` event on a file input yourself.** `bsk upload` already fires the handler; a second, hand-made event runs it twice and inserts the image twice. The dialog is simply slow — wait and count again.
- **The title is never auto-filled** — always do Step 6 explicitly, even though the body already looks complete after Step 5. Read the field back afterwards: a draft that reaches the draft box with an empty title looks finished in the editor and is not.
- **This skill only ever produces a draft.** It does not click 发布 under any circumstance, regardless of how the request is phrased.
- If Zhihu shows a captcha/risk-control challenge mid-flow, stop and ask the user to complete it manually in the browser rather than trying to click through it.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only (`certifi` is used for TLS if present, but is not required).
- The `bsk` CLI (macOS, Linux or Windows), plus its BrowserSkill extension installed in the user's Chromium browser **with "Allow access to file URLs" enabled**, and the user already logged into Zhihu. Step 4 gates on all three.
- For Notion sources, a connected Notion tool (`notion-fetch`) in this session.
