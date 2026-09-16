---
name: qingyun-md-2-zhihu
description: Publishes a Markdown article to the draft box of a Zhihu column (知乎专栏) in the user's own logged-in Chromium browser (Chrome or Edge), driven through whatever browser control the current agent has — its built-in browser extension (Claude in Chrome, Codex's Chrome plugin) or the agent-neutral `bsk` CLI. Handles three source shapes — a local .md file, a Notion page link, or another online markdown link — downloads any images to disk (immediately, before Notion's signed image URLs expire), uploads them to the public image host img.scdn.io so Zhihu's markdown import places and re-hosts them itself, imports the markdown into the Zhihu editor, fills in the title, inserts by hand only the images the host rejected, and verifies every image is in its correct position. Mode `--image-hosting no` keeps images off the public host and inserts every one by hand; `--driver` forces a specific browser driver. Stops at the draft stage — never publishes. Triggers on "发到知乎", "知乎草稿", "md-2-zhihu", "publish to zhihu", or a Zhihu draft-box request paired with a markdown/Notion source.
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
| `--image-hosting` | option | `yes` / `no` | `yes` | `yes` uploads every image to the public host img.scdn.io so Zhihu's import places it; an image the host rejects (unsupported type, over its size limit, host unreachable) falls back to manual insertion in Step 8. `no` is for images that must not be public — anything on img.scdn.io can surface on its explore page and random-image API — and inserts every image by hand. |
| `--driver` | option | `auto` / `claude-in-chrome` / `codex-chrome` / `bsk` | `auto` | How Step 4 reaches the browser. `auto` identifies the agent this skill is running in and takes that agent's first usable driver from `references/browser-drivers.md`. A named driver is for a user who prefers one, or for testing a driver the agent would not pick on its own; the run stops if that driver is unavailable. |

## Workflow

### Step 1 — Resolve `--source` and `--title`

Classify `--source` (local path / Notion link / other online link) and state the classification before proceeding. State `--image-hosting` too, and when it is `yes` (the default) say that the article's images will be uploaded to a public host. If `--title` wasn't given, say where the title will come from: the source's first heading for a local file or an online markdown link, or `properties.title` for a Notion page, which Step 2 lifts out separately. State `--driver` as given; Step 4 resolves `auto`.

If the source is a Notion page, run Step 4 up to and including its setup gate now, before Step 2 — see the note there.

### Step 2 — Get the article onto local disk

- **Local path**: nothing to do, go to Step 3.
- **Notion link**: fetch the page with the Notion tool connected to this agent (`notion-fetch`; in Claude Code, load it with `ToolSearch` first). Write the `<content>` block to a local `.md` file (a scratch or temporary directory), and note the page's `properties.title` — Notion returns the title there, **not** inside `<content>`, so it has to be passed to Step 3 as `--title`. **Do not do anything else — including opening the browser — between this step and Step 3.** Notion's image links are presigned and expire in roughly 5 minutes; Step 3 downloads every image immediately, so the two steps must run back to back in the same turn.
- **Other online link**: fetch the content directly (the agent's web-fetch tool, or a direct download) and save it to a local `.md` file the same way.

**This file is raw input for the script, not a document.** Nothing reads it but Step 3, which is the only thing in this skill that decides markdown formatting — block separation, indentation, lists and tables are all its job, and it does them the same way every run. Your job here is a byte-for-byte transfer and nothing else. Go straight from writing the file to running Step 3 on it.

**Copy the content out character for character.** The article's text passes through your own output on its way to disk, which is the one place in this skill where the author's words can be altered, and every alteration is invisible from here on. Specifically: do not add or remove blank lines — **not even around images, and not "just where it obviously needs one"** — do not change quote characters (`“ ”` are not `"`), do not drop or rewrite inline links, do not unescape anything, do not "tidy" indentation, and do not reformat tables — Step 3 converts raw `<table>` HTML to a pipe table itself, which is what gives Zhihu a real header row. **Do not repair the markdown either** — Step 3's script normalizes block separation, indentation and lists deterministically, and it can only do that correctly if what reaches it is what the source actually said. The title is the single exception: it is lifted out separately, as `--title`.

### Step 3 — Process the markdown (script)

Run:
```
python3 qingyun-md-2-zhihu/scripts/script.py --source <local-md-path> [--title "<title>"] [--image-hosting no]
```
For a Notion source, `--title` is required, not optional — the page title never appears in the body, and the script aborts rather than importing an untitled draft.
Pass `--image-hosting no` only when `--image-hosting` is `no`.
This normalizes block separation (see below), extracts the title (or uses `--title`), flattens every list so each item is a single block (see below), downloads every remote image / copies every local image referenced in the markdown, and replaces each image with a plain-text placeholder (`【ZHIHU-IMG-N】`) on its own paragraph. Unless `--image-hosting` is `no`, it then uploads each image to img.scdn.io and swaps its placeholder for a markdown image at the hosted URL (see below). It prints a JSON manifest: `title`, `processed_markdown` (path), `images_dir`, `image_hosting`, `images[]` (in document order, each with `index`, `local_path`, `hosted_url` and `placeholder` — exactly one of the last two is set, and an image that fell back to a placeholder also carries `hosting_error`), `blank_lines_inserted`, `soft_wrapped_lines`, `expected_structure` (including `images`, the hosted image blocks, and `placeholders`), `warnings[]`, and `errors[]`.

**Why images are hosted.** Zhihu's importer copies any public `https` image in the markdown onto its own CDN, in place — but it cannot fetch a local file, so a local image reference fails every time. Uploading each image to a public host first turns it into one the importer can fetch, which leaves nothing to insert by hand. The script paces uploads to the host's rate limit, and an image the host refuses keeps its placeholder, so that one image degrades to manual insertion instead of failing the run.

**Why block separation is normalized.** Markdown starts a new block on a *blank* line; a single newline is only a soft wrap. `notion-fetch` returns one block per line with no blank lines at all, and imported that way every consecutive paragraph fuses into one, a paragraph next to a list is swallowed into the list item above it, and a list beginning `1.` silently continues the previous list instead of starting its own. The script decides per adjacent pair rather than per file, so a source that has blank lines in some places and not others — around its images but not its paragraphs, say — is repaired everywhere it needs to be. A file that is already well-formed has no adjacent block lines to act on and comes through byte-identical. Where two paragraph lines meet, the line above is what decides: ending on sentence-final punctuation means two blocks, breaking mid-sentence means one soft-wrapped block, counted in `soft_wrapped_lines`.

**Why lists get flattened.** Zhihu's editor is Draft.js: its content is a flat run of blocks, with no `<ol start>` and no way to nest a block inside a list item. Any block that interrupts a run of list items — nested bullets, a sub-paragraph, a code block — closes the list, and the items after it open a **new** list that restarts at 1. The script therefore folds each item's nested content into the item itself using markdown hard breaks, which survive the import as line breaks inside that one item. Nested markers are demoted (`- ` → `• `, `1. ` → `1）`) so they aren't re-parsed as a nested list.

If `errors` is non-empty, stop and report exactly which images failed to download before continuing — a silently-dropped image is not acceptable. If `warnings` is non-empty, relay them: they name list content the script could not flatten, so that list will still break where the warning says, and every image that could not be hosted, which Step 8 will insert by hand. If every image fell back with `host unreachable`, say so plainly — img.scdn.io is blocked from this machine (a proxy is the usual cause), and the whole article goes through Step 8.

### Step 4 — Choose the browser driver, then open the Zhihu editor

Every browser action from here to Step 10 goes through one **driver**: the mechanism this agent has for controlling the user's own logged-in browser. Choose it before touching the browser, and use only that driver for the rest of the run.

1. **Identify the agent you are running in** — from your own system prompt, product name and tool list (Claude Code, Codex, or another harness). Say which it is.
2. **Pick the driver.** With `--driver auto`, first inventory what this agent can drive a browser with itself — its own tools, a bundled browser plugin, or an attached browser MCP server — and use that when it meets the checklist below; `references/browser-drivers.md` names the drivers already identified, but an agent absent from that list may still have one, so look before falling back. Use `bsk` only when the agent has no browser capability of its own or that capability fails the checklist. With a named `--driver`, use that one and stop if it is unavailable. State the chosen driver and the verification status the reference gives it.
3. **Check the driver can do everything this skill needs.** A driver is usable only if it can:
   - open or reuse a tab in the user's own logged-in browser — never a separate browser instance, a copied profile, or a browser launched with a debug port;
   - run JavaScript in the page and return its value, awaiting a promise;
   - click an element and press keys with real input, including Shift combinations;
   - put a local file into a page `<input type="file">` without leaving a native file picker open;
   - take a screenshot.

   If any is missing, stop and tell the user which one. Do not improvise a substitute.
4. **Clear the driver's setup gate** exactly as its section in the reference describes — for example, the file-URL permission an extension needs before its first upload. **When the source is a Notion page, clear this gate before Step 2**: Notion's signed image URLs expire in about five minutes, and a setup failure discovered after the fetch burns that window.
5. **Open the editor.** Reuse a `zhuanlan.zhihu.com` tab the driver already controls, otherwise open `https://zhuanlan.zhihu.com/write`. Then read which browser you are actually in, and whether the page is visible — never assume the brand, because an extension driver attaches to whichever Chromium browser it is connected to, Edge as readily as Chrome:

   ```js
   (() => JSON.stringify({
     browser: (navigator.userAgentData && navigator.userAgentData.brands.map(b => b.brand)) || navigator.userAgent,
     visibility: document.visibilityState,
     title: document.title
   }))()
   ```

   State the browser you got back; every later request for the user to look at or click something has to name it, or they will search the wrong application.
6. **Note the visibility, but carry on.** A tab a driver opened is normally a *background* tab, so `visibility` usually reads `hidden` — that is the ordinary case, not a fault, and it does not stop the run. What the editor needs is **focus**, and a real click through the driver grants it (`document.hasFocus()` becomes true even in a hidden tab), which is why every step that manipulates the page starts with a driver click rather than a synthetic one. Record what you read; `references/browser-drivers.md` says what to do if the page later stalls.
7. **Wait for the editor to accept input.** Poll `document.title` until it contains `写文章` before any click — the editor renders its content before it accepts input, and a click that lands too early can wedge the tab.

If the page shows a login wall instead of the editor, stop and ask the user to log into Zhihu in that browser — through the driver's human-help mechanism if it has one — then re-check.

**Page JavaScript.** Every snippet in this skill is a self-contained arrow function invoked in place — `(() => { … })()`, or `(async () => { … })()` when it awaits — returning `JSON.stringify(...)` of its result. Some drivers keep one global scope across calls, so a bare `const x` collides with the next snippet that reuses the name; some serialize objects poorly. This shape runs unchanged on every driver in the reference. Keep it for any snippet you add.

### Step 5 — Import the processed markdown

Click 导入 in the toolbar (`button[aria-label="导入"]`), then the 导入文档 MD/Doc menu item (`button[aria-label="导入文档"]`). A dialog opens on a 导入文档 / 导入链接 tab pair; make sure 导入文档 is the active tab. **Never click the file input yourself** — that opens a native file picker automation cannot fill. Hand the input to the driver's upload action instead.

**Targeting a file input.** The page carries several `<input type="file">`, and more than one matches any loose description — the attachment input accepts `.md` too, so "the markdown input" is ambiguous and picking the wrong one fails in ways that look like success. Select by the `accept` attribute in page JS, which is exact, and tag the winner so the upload can address it — with a data attribute for drivers that take a CSS selector, and an `aria-label` for drivers that find elements by name:

```js
(() => {
  const input = Array.from(document.querySelectorAll('input[type=file]'))
    .find(el => el.accept.includes('.markdown'));   // the MD/Doc import input
  if (!input) return JSON.stringify({ error: 'import input not found' });
  input.setAttribute('data-zh-input', 'import');
  input.setAttribute('aria-label', 'ZHIHU-IMPORT-INPUT');
  return JSON.stringify({ accept: input.accept });
})()
```

Print the chosen `accept` and check it before uploading — that one line is what separates the right input from a silent misfire. Then upload the manifest's `processed_markdown` to that input with the driver's upload action.

Conversion is finished when the editor body shows the article. Zhihu changes the URL to `/p/<article-id>/edit` only when it first saves the draft, which can lag the import — do not wait on the URL before carrying on. Read the id from `location.href` once it appears, and in any case before Step 9, which needs it. See `references/zhihu-editor-notes.md` for the underlying `document/convert` call.

If `expected_structure.images` is above 0, the importer then re-hosts those images onto Zhihu's CDN by itself. Poll until the editor holds exactly that many images and none is still pending:

```js
(() => {
  const imgs = Array.from(document.querySelectorAll('.public-DraftEditor-content img'));
  return JSON.stringify({
    url: location.href,
    count: imgs.length,
    pending: imgs.filter(i => !i.src.startsWith('https://pic')).length
  });
})()
```

A block that reads 上传失败 gets its **重试** button. If the retry fails too, stop and restart from Step 3 with `--image-hosting no`: a hosted image has no placeholder to fall back to once it is in the editor.

### Step 6 — Set the title

Put the manifest's `title` into `textarea[placeholder*="请输入标题"]`. Zhihu never derives the title from imported content, so this step is required even though Step 5 populated the body. It is a React-controlled input, so a plain `value =` assignment is ignored — use the native setter followed by an `input` event:

```js
(() => {
  const ta = document.querySelector('textarea[placeholder*="请输入标题"]');
  const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
  set.call(ta, '<title>');
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  return JSON.stringify({ title: ta.value });
})()
```

Confirm the returned `title` equals the manifest's `title`. An empty title field is invisible in a body-focused screenshot, and the draft still looks complete.

### Step 7 — Verify the imported body against the manifest, before touching images

Zhihu's converter can merge, split or swallow blocks in ways that still read plausibly on screen, so check the structure it actually built against the structure the script said to expect — not against your memory of the article:

```js
(() => {
  const ed = document.querySelector('.public-DraftEditor-content');
  const top = Array.from(ed.children[0].children);
  const imgs = Array.from(ed.querySelectorAll('img'));
  return JSON.stringify({
    paragraphs: top.filter(n => n.tagName === 'DIV').length,
    blockquotes: top.filter(n => n.tagName === 'BLOCKQUOTE').length,
    lists: top.filter(n => n.tagName === 'OL' || n.tagName === 'UL')
              .map(n => ({ type: n.tagName.toLowerCase(), items: n.children.length })),
    tables: Array.from(ed.querySelectorAll('table'))
              .map(t => ({ rows: t.querySelectorAll('tr').length })),
    images: imgs.length,
    unhosted: imgs.filter(i => !i.src.startsWith('https://pic')).length,
    placeholders: ed.innerText.match(/ZHIHU-IMG-\d+/g) || []
  });
})()
```

Against the manifest's `expected_structure`, every one of these must hold:

| Check | Requirement | What a mismatch means |
|---|---|---|
| `lists` | identical, in order — same count, same types, same item counts | items fused into one list, or one list split into several that renumber from 1 |
| `tables` | same row counts | the table was mangled or partly absorbed |
| `blockquotes` | same count | adjacent quotes merged, or a paragraph was absorbed into one |
| `placeholders` | same count as `expected_structure.placeholders`, in manifest order | an image position was lost |
| `images` | equals `expected_structure.images`, with `unhosted` at 0 | a hosted image was dropped, or has not finished re-hosting (go back to Step 5's poll) |
| `paragraphs` | **at least** `expected_structure.paragraphs` | fewer means paragraphs merged or got swallowed into a neighbouring block. (More is fine — Draft.js keeps a trailing empty block, and it wraps some blocks in an extra `div`.) |

Also confirm that no raw image markdown or URL leaked through unconverted.

**What this check cannot see.** `expected_structure` is computed from the processed markdown, so it proves Zhihu imported the script's output faithfully — not that the article reaching the script was intact. If Step 2 lost blank lines, the manifest and the editor agree on a paragraph count that is simply too low, and every row above passes. So before trusting it, sanity-check the manifest itself against the article you fetched: `expected_structure.paragraphs` should be in the range the source's own paragraphs suggest, and a non-empty `soft_wrapped_lines` on a source that isn't hard-wrapped prose means paragraphs arrived already joined. Relay any `warnings[]` rather than reading past them.

**On any mismatch, stop and report the two structures side by side.** Do not hand-patch the editor to make the numbers agree — the content has to be right in the markdown handed to the importer, so the fix belongs in Step 2 (something was altered on the way to disk) or in the script. Never skip ahead to image insertion with a mismatch outstanding: images are placed by finding placeholders, and a mangled body puts them in the wrong place.

### Step 8 — Insert every image that kept a placeholder, in order

Only images whose manifest entry has a `placeholder` are inserted here: every image when `--image-hosting` is `no`, otherwise only the ones carrying a `hosting_error`. If no image has a placeholder, skip Step 8 and continue to Step 9.

Each image replaces its own placeholder, one at a time, in manifest order. It lands wherever the editor's cursor is, so the cursor is placed deliberately every time — and success is judged by the editor's image count and the image's neighbours, never by the dialog's wording, which varies from upload to upload.

**Give the page focus with a driver click before selecting**, which each iteration does anyway by clicking the tagged span. Keyboard selection then works whether or not the tab is visible. Only if a selection comes back empty, or a page call times out, go to the stall remedy in `references/browser-drivers.md`.

For each image in the manifest that has a `placeholder`, **in order, one at a time**:

1. **Close any dialog left open.** The image dialog does not reliably close itself, and while it is open it swallows every click that follows — the symptom is an empty selection, which reads like a broken selector rather than a modal in the way. Check, press Escape, and check again until it is gone; one press does not always take:

   ```js
   (() => JSON.stringify({ dialogOpen: !!document.querySelector('.Modal') }))()
   ```

2. **Find the placeholder and record where it is.** Scroll its block to the middle of the viewport, record its block index and the label of the block before and after it — those are the anchor that proves, later, that the image landed where the placeholder was — and tag the innermost `span` holding the text. Tag the span, not the block: the block spans the full editor width, and a click at its centre can land past the end of a short placeholder. Replace `N` with the image's index:

   ```js
   (() => {
     const ed = document.querySelector('.public-DraftEditor-content');
     const top = Array.from(ed.children[0].children);
     const label = n => !n ? '' : n.querySelector('img') ? '[image]'
       : (n.innerText || '').replace(/\n/g, '').trim().slice(0, 20);
     const i = top.findIndex(n => n.innerText.includes('【ZHIHU-IMG-N】'));
     if (i < 0) return JSON.stringify({ error: 'placeholder not found' });
     top[i].scrollIntoView({ block: 'center' });
     const spans = Array.from(top[i].querySelectorAll('span'))
       .filter(s => s.textContent.includes('ZHIHU-IMG-N'));
     spans[spans.length - 1].setAttribute('data-zhtext', 'N');
     return JSON.stringify({
       index: i, prev: label(top[i - 1]), next: label(top[i + 1]),
       imgCount: ed.querySelectorAll('img').length
     });
   })()
   ```

3. **Select it with the keyboard.** Click the tagged span (`[data-zhtext="N"]`), press End, then press Shift+Home. Confirm `window.getSelection().toString()` contains `ZHIHU-IMG-N`; if it doesn't, repeat the three actions up to three times, then abort this image. Keyboard selection works whether or not the browser window is frontmost. A triple-click selects only in a frontmost window, and a `Range` set programmatically is ignored — Draft.js honours only selections made by real input.

4. **Clear it, and prove the cursor is in place.** Press Backspace, then check that an empty block sits at the recorded index, between the recorded neighbours, holding the caret:

   ```js
   (() => {
     const I = /* recorded index */, PREV = '/* recorded prev */', NEXT = '/* recorded next */';
     const ed = document.querySelector('.public-DraftEditor-content');
     const top = Array.from(ed.children[0].children);
     const label = n => !n ? '' : n.querySelector('img') ? '[image]'
       : (n.innerText || '').replace(/\n/g, '').trim().slice(0, 20);
     const sel = window.getSelection();
     const caret = sel.anchorNode ? top.findIndex(n => n.contains(sel.anchorNode)) : -1;
     return JSON.stringify({
       ok: label(top[I]) === '' && label(top[I - 1]) === PREV
           && label(top[I + 1]) === NEXT && caret === I,
       gap: label(top[I]), prev: label(top[I - 1]), next: label(top[I + 1]), caret
     });
   })()
   ```

   If the paragraph collapsed instead — the selection can take the line break with it, and Backspace then removes the whole block and leaves the caret on a neighbour — recreate the empty block from the recorded **following** block: click on its first line, press Home, press Enter to push it down, then ArrowUp into the new empty block, and run the check again. Never build it from the preceding block with End then Enter: End goes to the end of the visual line, not the block, so on a wrapped paragraph that splits the author's text mid-sentence. Do not open the dialog until `ok` is `true`. From here until the insert lands, the anchor exists only in what you recorded in step 2.

5. **Open the dialog and resolve its file input.** Open it only now, with the cursor parked — a file set while the editor holds no cursor is accepted by the dialog and then goes nowhere. Click the toolbar button in page JS, since element references can go stale each time a dialog opens and closes. Address it by `aria-label`: a toolbar button's `innerText` begins with a zero-width space and a line break, so matching on its text fails.

   ```js
   (() => {
     const b = document.querySelector('button[aria-label="图片"]');
     if (!b) return JSON.stringify({ error: 'image toolbar button not found' });
     b.click();
     return JSON.stringify({ opened: true });
   })()
   ```

   Then tag the input whose `accept` **starts with** `image/webp,image/jpg,image/jpeg,image/png`, the same way as Step 5, with `data-zh-input="image"` and `aria-label="ZHIHU-IMAGE-INPUT"`. Match on that prefix: the 附件 input takes `.png`/`.jpg` among a list of document types and inserts a file-name card instead of a picture, and another input accepts a bare `image/*`. Print the chosen `accept` and confirm it before uploading.

6. **Upload.** Give the image's `local_path` to the driver's upload action on that input. The action fires the input's change handler itself; never dispatch a `change` or `input` event in page JS to hurry it along — the handler then runs twice and inserts the image twice.

7. **Wait for the insert, by counting.** Poll the editor's `img` count until it is exactly one higher than step 2 recorded. Usually the image lands on its own and the dialog falls back to its start page. If the count has not risen but a 插入图片 button is on screen, click it — that completes the insert; dismissing the dialog at that point would throw the upload away. Then poll the new image's `src` until it is an `https://pic…` URL: an image can be placed before its upload finishes, with a `blob:` src. If its block reads 上传失败 instead, click its **重试** button; that recovers it in place.

8. **Confirm it landed in the right place**, not merely that it landed:

   ```js
   (() => {
     const I = /* recorded index */, PREV = '/* recorded prev */', NEXT = '/* recorded next */';
     const ed = document.querySelector('.public-DraftEditor-content');
     const top = Array.from(ed.children[0].children);
     const label = n => !n ? '' : n.querySelector('img') ? '[image]'
       : (n.innerText || '').replace(/\n/g, '').trim().slice(0, 20);
     const img = top[I] && top[I].querySelector('img');
     return JSON.stringify({
       imgCount: ed.querySelectorAll('img').length,
       inPlace: !!img && label(top[I - 1]) === PREV && label(top[I + 1]) === NEXT,
       src: img ? img.src.slice(0, 40) : null,
       size: img ? [img.naturalWidth, img.naturalHeight] : null
     });
   })()
   ```

   `inPlace` must be `true`, `imgCount` exactly one higher than step 2 recorded, and `size` must match the local file's dimensions. A count that rose while the neighbours changed means the image went in at a stale cursor — which is precisely what a count-only check cannot see.

**When the check fails, what to do depends on how it failed.** Two of these are repairable in place; only the last needs a rebuild.

| Symptom | Fix |
|---|---|
| The count rose by two — the same image inserted twice | Delete the extra figure with its **×** control (below), then re-run the check. The surviving image is normally in the right place; the recorded neighbours will confirm it. Caused by dispatching an upload event by hand — don't. |
| The block reads 上传失败 | Click **重试** on that block. It uploads in place and keeps its position. |
| The image sits between the wrong neighbours, or went in as a file-name card | **Rebuild.** Its placeholder was consumed in step 4, so there is no anchor left to retry against, and an undo restores the text without restoring the cursor. Clear the body, re-import from Step 5, and start the loop again. |

Do not carry on inserting the remaining images into a draft that is already wrong — but equally, do not rebuild a draft whose only problem is a duplicate you can delete.

**Deleting a figure.** An image block is atomic and Backspace will not remove it. Its **×** control appears on hover, and a hover followed by a separate click races the control's own visibility, so click it in page JS:

```js
(() => {
  const fig = /* the figure to delete */;
  const x = fig.querySelector('.ZDI--Xmark24');
  const c = x.closest('button') || x.closest('[role=button]') || x.parentElement;
  c.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
  c.click();
  return JSON.stringify({ deleted: true });
})()
```

### Step 9 — Verify against the server, not just the screen

The editor's DOM can be ahead of what Zhihu has actually stored, and autosave lags (it can sit on 草稿保存中 for minutes). **Do this before ending the driver session** — ending it can discard anything autosave has not yet flushed, and an image that was visible in the editor is simply gone.

Run the check first and only look at visibility if it disagrees: a page hidden for a while can sit on the very save you are checking for, which is the remedy below, not a reason to interrupt the user beforehand.

```js
(async () => {
  const r = await fetch('/api/articles/<article-id>/draft', { credentials: 'include' });
  const d = await r.json();
  const doc = new DOMParser().parseFromString(d.content || '', 'text/html');
  const imgs = Array.from(doc.querySelectorAll('img'));
  return JSON.stringify({
    status: r.status, state: d.state, title: d.title,
    imgs: imgs.length,
    notOnZhihu: imgs.map(i => i.getAttribute('src') || '').filter(s => !s.startsWith('https://pic')),
    placeholders: (d.content || '').match(/ZHIHU-IMG-\d+/g) || [],
    order: Array.from(doc.body.children).map(n => {
      const img = n.tagName === 'IMG' ? n : n.querySelector('img');
      return img ? '[image]' : (n.textContent || '').trim().slice(0, 12);
    }).filter(Boolean)
  });
})()
```

Confirm in the **returned content**: `imgs` equals the number of entries in the manifest's `images`, `notOnZhihu` and `placeholders` are empty, `title` is the manifest's `title`, and `state` is `draft`. If the server copy lags, check `document.visibilityState` first. Once a tab has been hidden for more than a few seconds, the browser throttles its timers so hard that a change made after that point — observed with inserted images — may not be saved until the tab is visible again: no save request goes out, and the indicator sits on 草稿保存中. The save goes out within seconds of the tab becoming visible. A network fault looks different: the save request is sent and fails. So bring the tab to the front (ask the user if the driver cannot), wait, and re-read. Reload the edit URL only as a last resort, accepting the "Leave site?" prompt: a reload can lose edits autosave never sent. Only report success on the server-side copy.

Then check the images are in the right **places**, which a count cannot tell you. `order` lists the saved blocks in sequence — Zhihu stores an image as a top-level `<img>`, not always inside a wrapper, which is why the snippet checks the element itself. Confirm each `[image]` sits between the same two pieces of text it sits between in the processed markdown: image N should follow the paragraph that precedes its marker in `processed_markdown` and precede the one that follows it. The marker is the `![](<hosted_url>)` line for a hosted image, and `【ZHIHU-IMG-N】` for one inserted by hand. Report the first mismatch with both orderings rather than a summary; an image in the wrong position is invisible in every count-based check and in a screenshot of any other part of the article.

### Step 10 — Hand off to the user

End the driver session as its section in `references/browser-drivers.md` describes — only after Step 9 has confirmed the server copy, and on failure paths too rather than leaving it to an idle timeout.

Report back: the draft URL (`zhuanlan.zhihu.com/p/<id>`), the title used, the image count, and a screenshot of the finished draft. **Never click 发布 (publish)** — the article stays in the draft box for the user to review and publish themselves.

## Output

A short report to the user: draft URL, title, number of images placed, and a screenshot of the finished draft — nothing else changes on their account.

## Gotchas

- **Zhihu's importer re-hosts only images it can fetch.** A public `https` image URL is copied onto Zhihu's CDN in place; a local or relative path fails every time (`400 图片地址不合法`). That is why Step 3 never lets a local image reference reach the importer: each image is either hosted publicly or replaced by a placeholder. See `references/zhihu-editor-notes.md`.
- **img.scdn.io is a public host.** An uploaded image can surface on its explore page and random-image API, and the host AI-tags and describes it. Use `--image-hosting no` for any article whose images must not be public, and name the hosting mode in Step 1.
- **A blocked image host looks like a slow, normal run.** If img.scdn.io is unreachable, every image falls back with `host unreachable` and Step 8 inserts them all by hand. Relay it from `warnings` so the user knows why hosting did nothing.
- **A single newline is not a paragraph break.** Markdown starts a new block only on a *blank* line, and `notion-fetch` returns one block per line with none. Left uncorrected this fuses consecutive paragraphs, absorbs a paragraph next to a list into the item above it, merges adjacent blockquotes, and makes a `1.` list continue the previous list rather than start its own — all of it looking like a plausible article on screen. Step 3 normalizes this; Step 7 catches whatever it missed.
- **Anything you retype can be altered without you noticing.** The Notion path routes the article through your own output on the way to disk. Observed drift from real runs: 40 blank lines dropped, the title lost, 20 curly quotes flattened to straight ones, two inline links silently removed — and, in another run, blank lines added around the images but not between the paragraphs, which merged every paragraph run in the finished draft. Improving the formatting is as damaging as degrading it; Step 3 is the only thing that decides format.
- **The manifest is not independent evidence of the input.** `expected_structure` is derived from the processed markdown, so a source that arrived already merged produces a manifest and an editor that agree with each other and disagree with the article. Step 7 catches Zhihu mangling the import; only reading the manifest against the source catches Step 2 mangling the article.
- **Draft.js restarts ordered-list numbering at every interruption.** There is no `<ol start>` in Zhihu's editor, and a list item cannot contain a nested block. Any block between two items — nested bullets, a sub-paragraph, an image — ends the list, and the following items render as 1, 2, 3 again no matter what the source markdown said. Step 3's flattening pass exists for this; Step 7 verifies it held. Tab-indented lines are a related hazard: outside a list a tab-indented line imports as a `<pre>` code block.
- **Notion image links expire in ~5 minutes.** Steps 2 and 3 must run back to back with nothing else in between when the source is a Notion page, and the driver's setup gate must already be clear.
- **The driver is whatever this agent has, not a fixed tool.** Identify the agent and choose from `references/browser-drivers.md` every run; never assume a tool from a previous run or another agent still exists, and never fall back to launching a separate browser.
- **The image dialog's wording is not a signal.** An upload can land at the cursor immediately, with no 已上传 N 张图片 footer and no 插入图片 button, or it can wait for 插入图片 — and dismissing a dialog that is still waiting throws the upload away with no error. Judge by the editor's image count.
- **Several file inputs match any loose description, and the wrong one fails like a success.** The image dialog's `accept` starts `image/webp,image/jpg,image/jpeg,image/png`, while the 附件 input accepts `.png`/`.jpg` alongside `.pdf`/`.md`/`.doc`, the article-cover input accepts `.jpeg, .jpg, .png`, and a further input accepts a bare `image/*`. Uploading an image to the attachment input turns the dialog button into 添加文件 and inserts a file-name card, not a picture. Select by `accept` in page JS and print it before uploading.
- **Toolbar buttons are named by `aria-label`, not by their text.** Their `innerText` is `"​\n图片"` — a zero-width space and a line break before the label — and `trim()` does not strip the zero-width space, so an exact text match finds nothing. Use `button[aria-label="图片"]`, `button[aria-label="导入"]`.
- **A count going up is not the image being in the right place.** The insert lands wherever the cursor happens to be, so a stale cursor produces a draft with the right number of images, all with valid CDN URLs, no placeholders left — and a picture several paragraphs from where it belongs. Only a neighbour check catches it, which is why Steps 8 and 9 record and compare the surrounding text.
- **Never judge an inserted image by what it depicts.** An article about a codebase legitimately contains screenshots of folder trees, editors, and terminals that can look like stray UI from your own environment. Verify by dimensions against the local file (`sips -g pixelWidth -g pixelHeight` on macOS), or open the local file and look — never by assuming what the picture "should" show.
- **Prefer keyboard selection over a triple-click.** A triple-click needs the page to hold focus — which a driver's own click grants, so it often works — but it can take the placeholder's trailing line break with it, and it selects nothing in a window driven with focus withheld. Click, End, Shift+Home behaves the same in every case.
- **The image dialog does not reliably close itself.** A dialog left open eats every later click; clear it at the top of every image iteration and re-check after each Escape.
- **A file set while the editor holds no cursor goes nowhere.** The dialog accepts the upload, no image appears, no error is raised. Place the cursor first, then open the dialog — never the other way round.
- **Ending the driver session can discard unsaved work.** An image visible in the editor but not yet autosaved can be lost when the session or tab goes away. Confirm the server copy in Step 9 first.
- **A freshly loaded `/edit` page can render content while still ignoring all input.** Until the tab title reads `写文章 - 知乎` rather than `知乎 - 知乎`, the app has not finished booting — typing has no effect, and a click can wedge the tab. Poll the title before acting.
- **The browser may not be Chrome.** An extension driver attaches to whichever Chromium browser it is connected to — Edge as often as Chrome — and `bsk` opens its Agent Window in that same browser. Read the brand from the page (`navigator.userAgentData.brands`) and name it whenever you ask the user to look at or click a tab; a request to check "Chrome" sends them to an application that has nothing in it.
- **An open window is not a visible page, and focus is not visibility.** A tab an extension driver opens starts as a *background* tab: it can sit in a window the user is watching while its page reports `visibilityState: 'hidden'`, and a click through the driver sets `document.hasFocus()` to true without changing that. So a click-driven flow selects and types normally while its timers stay throttled — script calls time out, and a change made once the page has been hidden a while is not saved until it is visible again (measured with an inserted image; a change made within a few seconds of hiding still saved). Read `visibilityState` itself: neither an open window, nor focus, nor the user saying they see the browser settles it.
- **An image block is atomic: Backspace/Delete will not remove it, but the UI will.** Its **×** control deletes it, and a block showing 上传失败 carries a **重试** button that re-uploads it in place. Reach for those before rebuilding the draft — an image that failed or got inserted twice is repairable, and only a wrongly-positioned one is not.
- **A placed image is not necessarily on the CDN yet.** The block can appear with a `blob:` src and finish uploading afterwards, or show 上传失败 — sometimes only because the editor stopped waiting while Zhihu's server was still processing the image. Poll the `src` until it is a `pic…` URL, and use 重试 on a failed block.
- **Never dispatch a `change` or `input` event on a file input yourself.** The driver's upload action already fires the handler; a second, hand-made event runs it twice and inserts the image twice. The dialog is simply slow — wait and count again.
- **The title is never auto-filled** — always do Step 6 explicitly, even though the body already looks complete after Step 5. Read the field back afterwards: a draft that reaches the draft box with an empty title looks finished in the editor and is not.
- **This skill only ever produces a draft.** It does not click 发布 under any circumstance, regardless of how the request is phrased.
- If Zhihu shows a captcha/risk-control challenge mid-flow, stop and ask the user to complete it manually in the browser — through the driver's human-help mechanism if it has one — rather than trying to click through it.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only (`certifi` is used for TLS if present, but is not required).
- Network access to `img.scdn.io` when `--image-hosting` is `yes` (API: `https://img.scdn.io/api_docs.php`).
- A Chromium browser (Chrome or Edge) with the user already logged into Zhihu, and one driver from `references/browser-drivers.md` that passes Step 4's capability check — the agent's own browser extension, or the `bsk` CLI with its extension.
- For Notion sources, a Notion fetch tool (`notion-fetch`) connected to the agent.
