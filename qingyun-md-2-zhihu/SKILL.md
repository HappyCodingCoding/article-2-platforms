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
| `--title` | option | any string | inferred from the source's first heading | Overrides auto-detected title. When inferred, the heading is also stripped from the body so it isn't shown twice (once as the Zhihu title field, once again as the first line of the article). When `--title` is given explicitly, the body is left untouched. |

## Workflow

### Step 1 — Resolve `--source` and `--title`

Classify `--source` (local path / Notion link / other online link) and state the classification before proceeding. If `--title` wasn't given, note that the title will be auto-detected from the first heading in Step 3.

### Step 2 — Get the article onto local disk

- **Local path**: nothing to do, go to Step 3.
- **Notion link**: load the Notion fetch tool (`ToolSearch` for `notion-fetch`) and call it on the URL to retrieve the page as Markdown-like text with inline image URLs. Save that text verbatim to a local `.md` file (scratchpad directory). **Do not do anything else — including opening the browser — between this step and Step 3.** Notion's image links are presigned and expire in roughly 5 minutes; Step 3 downloads every image immediately, so the two steps must run back to back in the same turn.
- **Other online link**: fetch the content directly (`WebFetch` or a direct download) and save it to a local `.md` file the same way.

### Step 3 — Process the markdown (script)

Run:
```
python3 qingyun-md-2-zhihu/scripts/script.py --source <local-md-path> [--title "<override>"]
```
This extracts the title (or uses `--title`), downloads every remote image / copies every local image referenced in the markdown, replaces each image with a plain-text placeholder (`【ZHIHU-IMG-N】`) on its own paragraph, and prints a JSON manifest: `title`, `processed_markdown` (path), `images_dir`, `images[]` (each with `index`, `placeholder`, `local_path`, in document order), and `errors[]`.

If `errors` is non-empty, stop and report exactly which images failed to download before continuing — a silently-dropped image is not acceptable.

### Step 4 — Load the browser tools and open the Zhihu editor

Load the needed Claude-in-Chrome tools in one `ToolSearch` call (`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__form_input`) if they aren't already loaded.

Use the **user's own connected Chrome** (Claude in Chrome) — never launch a separate browser instance with a debug port. Get the tab context, reuse an existing `zhuanlan.zhihu.com` tab if one is open, otherwise navigate a tab to `https://zhuanlan.zhihu.com/write`.

If the page shows a login wall instead of the editor, stop and use `AskUserQuestion` to ask the user to log into their Zhihu account in that browser, then re-check.

### Step 5 — Import the processed markdown

Click 导入 in the toolbar, then the 导入文档 MD/Doc menu item. A new `<input type="file">` appears whose `accept` contains `.md` — that is the import input (identify it by `accept`, not by position). Set it to the manifest's `processed_markdown` with the file-upload tool. **Do not click the input itself**; clicking opens a native file dialog that automation cannot drive.

Wait for the conversion to finish and the editor body to populate. The URL changes to `/p/<article-id>/edit` — record that id, Step 9 needs it. See `references/zhihu-editor-notes.md` for the underlying `document/convert` call.

### Step 6 — Set the title

Put the manifest's `title` into `textarea[placeholder*="请输入标题"]`. Zhihu never derives the title from imported content, so this step is required even though Step 5 populated the body. It is a React-controlled input, so a plain `value =` assignment is ignored — either type into it, or use the native setter followed by an `input` event.

### Step 7 — Verify the imported body before touching images

Read the editor's text and confirm every placeholder (`【ZHIHU-IMG-1】` … `【ZHIHU-IMG-N】`) is present, in order, and that no raw image markdown or URL leaked through unconverted. Fix Step 3 or re-run Step 5 if not — do not skip ahead to image insertion.

### Step 8 — Insert every image, in order

Zhihu's image dialog uploads the file first and inserts it on a second, explicit action — **the insert only happens when you click 插入图片**, and it lands at wherever the editor's cursor was. Both halves matter: skipping the button silently discards the upload, and an unset cursor puts the image in the wrong place.

For each image in the manifest, **in order, one at a time**:

1. **Select the placeholder.** In page JS, walk the editor's text nodes for `【ZHIHU-IMG-N】`, scroll it to mid-viewport (`window.scrollBy(0, rect.y - 400)`), read its `getBoundingClientRect()`, convert to click coordinates (Step 8a), and triple-click it. Confirm `window.getSelection().toString()` contains `ZHIHU-IMG-N` before going on; abort this image if it doesn't. Draft.js only honours a selection made by real input — a `Range` set programmatically is ignored.
2. **Clear it.** Press Backspace so the placeholder is gone and the cursor sits in the now-empty paragraph. That cursor is where the image will land.
3. **Open the dialog.** Click the 图片 toolbar button. A file input with `accept="image/*"` appears — identify it by that attribute. **Do not click the input**; clicking opens a native OS file dialog that automation cannot fill.
4. **Upload.** Set that input to the image's `local_path` with the file-upload tool. Wait for the dialog footer to read 已上传 N 张图片.
5. **Insert.** Click 插入图片. The dialog closes and the image appears at the cursor with an `https://pic…` src — it was uploaded to Zhihu's CDN during step 4, so there is no in-editor upload to wait out.
6. **Confirm** the editor's `<img>` count went up by one before starting the next image.

**Step 8a — click coordinates.** The click coordinate frame can differ from the page's CSS viewport; multiply JS coordinates by `frameWidth / window.innerWidth` (the screenshot result reports the frame; `innerWidth`/`innerHeight` come from the page). Skipping this lands clicks a few percent off, silently.

**Step 8b — clipboard paste (alternative).** Pasting a real image works too and is the flow a human uses: put the file on the system clipboard (macOS: `osascript -e 'set the clipboard to (read (POSIX file "…") as «class PNGf»)'`), select the placeholder, and send `cmd+v`. It inserts at the cursor and reaches the same CDN. Prefer the dialog flow above anyway, because paste: (a) reads a **shared** clipboard that any other app — or the user — can overwrite between the copy and the paste, which then silently pastes the wrong content instead of failing; (b) destroys whatever the user had on their clipboard; (c) is platform-specific; and (d) inserts first and uploads afterwards **inside** the editor, which is the state that stalls into 上传失败 and freezes autosave. Use it only when the dialog is unavailable, and re-copy immediately before each paste.

**Step 8c — local HTTP server + synthetic paste (alternative).** Also works, verified end to end for all images in a draft when paced correctly: run `python3 -m http.server <port>` (or equivalent) in `images_dir`, then in page JS `fetch` each image from `http://127.0.0.1:<port>/img-N.png`, wrap the blob in a `File`, put it in a `DataTransfer`, and dispatch `new ClipboardEvent('paste', {clipboardData, bubbles: true, cancelable: true})` on `.public-DraftEditor-content[contenteditable="true"]` — `defaultPrevented === true` means the editor took it. This reaches the exact same upload chain as Step 8b, just without touching the OS clipboard. Prefer the dialog flow anyway: this route needs page-JS execution for the insertion itself (the dialog needs it only to locate the placeholder), needs a server process started and torn down for exactly the right window, and depends on Chrome's Private Network Access policy continuing to allow an https page to fetch localhost — a policy that has been tightening across Chrome versions. The one-image-at-a-time rule from Step 8's intro applies here just as strictly: firing the next paste before the previous image's `src` becomes `https://pic…` is what stalls an upload into 上传失败.

### Step 9 — Verify against the server, not just the screen

The editor's DOM can be ahead of what Zhihu has actually stored, and autosave lags (it can sit on 草稿保存中 for minutes). Check the saved copy:

```
GET /api/articles/<article-id>/draft   (same-origin, credentials included)
```

Confirm in the **returned content**: `<img` count equals the manifest count, every one has an `https://pic…` src, no `ZHIHU-IMG` placeholder remains, and `state` is `draft`. If the server copy lags, force a flush by navigating to the same edit URL again (`force: true` — the "Leave site?" prompt is expected), then re-check. Only report success on the server-side copy.

### Step 10 — Hand off to the user

Report back: the draft URL (`zhuanlan.zhihu.com/p/<id>`), the title used, and the image count, with a screenshot of the finished draft. **Never click 发布 (publish)** — the article stays in the draft box for the user to review and publish themselves.

## Output

A short report to the user: draft URL, title, number of images placed, and a screenshot of the finished draft — nothing else changes on their account.

## Gotchas

- **Zhihu's own "reupload from markdown" step is broken for local images and will fail every time** (`400 图片地址不合法`) — this is exactly why Step 3 replaces images with placeholders before import instead of letting Zhihu try to fetch them itself. See `references/zhihu-editor-notes.md`.
- **Notion image links expire in ~5 minutes.** Steps 2 and 3 must run back to back with nothing else in between when the source is a Notion page.
- **Uploading is not inserting.** The image dialog uploads on file-select but only places the image when 插入图片 is clicked. Dismissing the dialog after upload (Escape, clicking away) throws the insertion away and leaves no error — it just looks like nothing happened.
- **Never judge an inserted image by what it depicts.** An article about a codebase legitimately contains screenshots of folder trees, editors, and terminals that can look like stray UI from your own environment. Verify by dimensions against the local file (`sips -g pixelWidth -g pixelHeight`), or open the local file and look — never by assuming what the picture "should" show.
- **Click coordinates may not equal page coordinates** — scale by `frameWidth / window.innerWidth` (Step 8a). A silently mis-landed click is easy to mistake for a broken editor.
- **A freshly loaded `/edit` page can render content while still ignoring all keyboard input.** If typing has no effect, the app has not finished booting (the tab title is still `知乎 - 知乎` rather than `写文章 - 知乎`) — wait or reload rather than concluding the editor is read-only.
- **An image block that is still uploading inside the editor cannot be removed by Backspace/Delete**, turns into 上传失败, and blocks autosave for the whole draft. Step 8 avoids this by uploading in the dialog before insertion; if you ever end up with one anyway, the draft is easier to rebuild than to repair.
- **The title is never auto-filled** — always do Step 6 explicitly, even though the body already looks complete after Step 5.
- **This skill only ever produces a draft.** It does not click 发布 under any circumstance, regardless of how the request is phrased.
- If Zhihu shows a captcha/risk-control challenge mid-flow, stop and ask the user to complete it manually in the browser rather than trying to click through it.

## Dependencies

- Python 3.8+ for `scripts/script.py` — standard library only (`certifi` is used for TLS if present, but is not required).
- A Chrome browser connected via Claude in Chrome, with the user already logged into Zhihu. Steps 7–9 need page-JS execution, so the browser tooling must include a JavaScript-evaluation capability.
- For Notion sources, a connected Notion tool (`notion-fetch`) in this session.
