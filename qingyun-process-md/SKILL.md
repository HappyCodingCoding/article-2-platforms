---
name: qingyun-process-md
description: Processes a Markdown article into self-contained markdown files ready to import into Chinese social platforms' editors. Handles three source shapes — a local .md file, a Notion page link, or another online markdown link — downloads every image to disk (immediately, before Notion's signed image URLs expire), normalizes block separation, lifts the title out of the body, then hosts every image publicly in one batch through the `qingyun-file-hosting` skill and points the markdown at the hosted URLs. `--platform` (`all` by default, or `unspecified` / `Zhihu` / `Weixin` / `RedNote`) picks which platform-tailored files to write — the Zhihu file also converts HTML tables to pipe tables, flattens nested lists and rewrites runs of one-line quotes and numbered lists in quotes as HTML; the Weixin file wraps numbered list items in `<li></li>`; RedNote shares the unspecified file for now. `--persistence` chooses between temporary and never-expiring image links; `--image-hosting no` keeps images off public hosts and leaves a placeholder for each. Hands back the processed files in `--output-dir` (default ~/Downloads/processed-mds); never opens a browser or publishes anything. Triggers on "process md", "处理 markdown", "把 md 里的图片传图床", "prepare this article for import", or a request to get a markdown/Notion article's images onto public URLs.
---

# Process Markdown

Takes one Markdown article — local file, Notion page, or another online link — and turns it into markdown files whose images are public URLs and whose blocks survive each target platform's markdown import, copied to `--output-dir` (`~/Downloads/processed-mds/` by default).

## Usage

Callable by explicit options or by natural language (infer `--source` from whatever path/link the user pastes; "for 知乎" → `--platform Zhihu`, "for 公众号 / 微信" → `--platform Weixin`, "for 小红书" → `--platform RedNote`; "links that won't expire" → `--persistence permanent`). Name any inferred option before running. If the source type is ambiguous (e.g. a bare string that could be a path or a broken URL), ask rather than guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `--source` | option (required) | local file path / Notion page URL / other online markdown URL | — | The article's source. Type is inferred: a path that exists on disk is local; a URL containing `notion.so` or `app.notion.com` is a Notion page; any other URL is fetched generically. |
| `--title` | option | any string | inferred from the source's first heading | Overrides auto-detected title. When inferred, the heading is also stripped from the body so it isn't shown twice (once in the platform's title field, once again as the first line of the article). When `--title` is given explicitly, the body is left untouched. For a Notion source, the title defaults to the page's `properties.title`, and the processed files keep it as their first line, `# <title>` — unless the page body already opens with a `# ` heading, which is then kept instead. A given `--title` replaces the page title there. |
| `--platform` | option | `all` / `unspecified` / `Zhihu` / `Weixin` / `RedNote` | `all` | Which platform-tailored files to write. Every file gets the processing any import needs — blank lines between blocks, the title lifted out, images hosted. `Zhihu` also converts HTML tables to pipe tables, flattens nested lists and rewrites some quotes as HTML, which Zhihu's editor needs (Step 3.1), and writes `<title>-zhihu.md`. `Weixin` also wraps each numbered list item outside a quote in `<li></li>` (Step 3.1), and writes `<title>-weixin.md`. `unspecified` applies nothing platform-specific and writes `<title>-unspecified.md`; `RedNote` has no processing of its own yet, so it writes that same unspecified file. `all` writes every distinct file — currently the unspecified, Zhihu and Weixin ones — from a single download and upload of the images. Matched regardless of case. |
| `--output-dir` | option | any directory path | `~/Downloads/processed-mds` | Where Step 4 delivers the finished `<title>-<variant>.md` file(s); created if missing. The working folder (`<source-name>-processed/`, with the images and manifest) stays next to the source regardless. |
| `--image-hosting` | option | `yes` / `no` | `yes` | `yes` uploads every image to public hosts through `qingyun-file-hosting` (Step 3.2) and points the markdown at the hosted URLs. `no` is for images that must not be public — every upload can be opened by anyone with its link and cannot be deleted — and skips Steps 3.2 and 3.3, so every image keeps its `【IMG-N】` placeholder for inserting by hand after import. |
| `--persistence` | option | `temporary` / `permanent` | `temporary` | Passed to `qingyun-file-hosting` in Step 3.2; ignored when `--image-hosting` is `no`. `temporary` lets images land on the most reliable hosts, most of which expire (the top one after 3 hours) — enough when the file is imported soon, since platforms like Zhihu copy imported images onto their own CDN. `permanent` keeps images to hosts whose links never expire, for a file that will be imported later or kept as a published copy. |

## Workflow

### Step 1 — Resolve `--source`, `--platform`, `--output-dir`, `--title`, `--image-hosting` and `--persistence`

Classify `--source` (local path / Notion link / other online link) and state the classification before proceeding. State `--platform` and the file(s) it will produce in `--output-dir`: `--platform all` → `<title>-unspecified.md`, `<title>-zhihu.md` and `<title>-weixin.md`; `--platform Zhihu` → `<title>-zhihu.md`; `--platform Weixin` → `<title>-weixin.md`; `--platform unspecified` or `--platform RedNote` → `<title>-unspecified.md` — for RedNote, say that no RedNote-specific processing exists yet. With `--image-hosting no`, say that no image leaves this machine and every image will stay a `【IMG-N】` placeholder. Otherwise say that the article's images will be uploaded to public hosts through `qingyun-file-hosting`, and state `--persistence`: with `temporary`, say the links will most likely expire within hours to weeks, so the file should be imported soon; with `permanent`, say the links never expire. If `--image-hosting` is `yes` and the user called the article's images private or confidential, point out that every upload is public and cannot be deleted, and wait for a go-ahead or a switch to `--image-hosting no`. If `--title` wasn't given, say where the title will come from: the source's first heading for a local file or an online markdown link, or `properties.title` for a Notion page, which Step 2 writes as the converted article's heading.

This step is a status line, not a question: go straight on to Step 2 unless something above needs the user's answer.

### Step 2 — Get the article onto local disk

- **Local path**: nothing to do, go to Step 3.
- **Notion link**: fetch the page with the Notion tool connected to this agent (`notion-fetch`; in Claude Code, load it with `ToolSearch` first). Write the `<content>` block — everything between `<content>` and `</content>`, nothing more — to `<name>.notion.md` in a scratch or temporary directory, and note the page's `properties.title`. Then convert it (script):
  ```
  python3 qingyun-process-md/scripts/script.py notion --input <name>.notion.md --title "<title>" --output <name>.md
  ```
  with `<title>` being `--title` if the user gave one, otherwise `properties.title`. `<name>.md` is the source for Step 3.1. Its first line is `# <title>`, unless the page body already opens with a `# ` heading of its own, which is then kept as the first line instead. Relay any `warnings` the conversion prints.
  **Do not do anything else between the fetch and Step 3.1.** Notion's image links are presigned and expire in roughly 5 minutes; Step 3.1 downloads every image immediately, so the fetch, the conversion and Step 3.1 must run back to back in the same turn.
- **Other online link**: fetch the content directly (the agent's web-fetch tool, or a direct download) and save it to a local `.md` file the same way.

**Why Notion content is converted.** `notion-fetch` returns Notion-flavored markdown, not the markdown the Notion app exports: children sit on tab-indented lines under their parent, rich text is backslash-escaped (`\~`), each block is one line with no blank line after it, and Notion-only syntax such as `<empty-block/>`, `{color="…"}` and `<callout>` appears inline. Read as standard markdown, a list inside a quote turns into a code block and every quote loses its closing line. The conversion rewrites all of it the way the Notion app's Export → Markdown does — checked byte for byte against a real export — so what reaches Step 3.1 is the same file the user would get from exporting the page themselves.

**The fetched file is raw input for the script, not a document.** Nothing reads it but the scripts, which alone decide markdown formatting — the Notion conversion, block separation, indentation, lists and tables are all their job, and they do them the same way every run. Your job here is a byte-for-byte transfer and nothing else. Go straight from writing the file to running the scripts on it.

**Copy the content out character for character.** The article's text passes through your own output on its way to disk, which is the one place in this skill where the author's words can be altered, and every alteration is invisible from here on. Specifically: do not add or remove blank lines — **not even around images, and not "just where it obviously needs one"** — do not change quote characters (`“ ”` are not `"`), do not drop or rewrite inline links, do not unescape anything (the Notion conversion unescapes exactly what Notion escaped), do not "tidy" indentation or turn tabs into spaces, and do not reformat tables or Notion tags — the scripts convert them. **Do not repair the markdown either** — the scripts can only do their work correctly if what reaches them is what the source actually said.

### Step 3 — Process the markdown and host its images

#### Step 3.1 — Prepare (script)

Run:
```
python3 qingyun-process-md/scripts/script.py prepare --source <local-md-path> [--platform <unspecified|zhihu|weixin|rednote>] [--title "<title>"]
```
Omit `--platform` at `all`. For a Notion source, `<local-md-path>` is the converted `<name>.md` from Step 2, and `--title` is the same `<title>` Step 2 converted with. Passing it explicitly leaves the body untouched, so the processed files keep that first line: the title from the Notion page stays in the article. For any source, the script aborts rather than produce an untitled article when there is neither a heading nor `--title`.

For each file `--platform` asks for, this normalizes block separation (see below), extracts the title (or uses `--title`), and replaces each image with a plain-text placeholder (`【IMG-N】`) on its own paragraph; the Zhihu file additionally gets its HTML tables converted, its lists flattened and some quotes rewritten as HTML, and the Weixin file its numbered list items wrapped in `<li></li>` (see below). Every image referenced in the markdown is downloaded (remote) or copied (local) once and shared by all the files. It writes `unspecified.md` and/or `zhihu.md`, `manifest.json` and `images/` into a `<source-name>-processed` folder next to the source, and prints the manifest: `title`, `platform`, `manifest` (path), `images_dir`, `images[]` (in document order, each with `index`, `local_path`, `source_url`, `placeholder` and `hosted_url`), `outputs[]` (one per file, each with `variant`, `processed_markdown` (path), `excluded_hosts` (hosts whose links that platform cannot show), `images[]` (that file's own `index`, `hosted_url` and `placeholder` per image), `blank_lines_inserted`, `soft_wrapped_lines`, `expected_structure` — including `images`, the hosted image blocks, and `placeholders` — and `warnings[]`), `warnings[]` (hosting), and `errors[]`.

**Why block separation is normalized.** Markdown starts a new block on a *blank* line; a single newline is only a soft wrap. `notion-fetch` returns one block per line with no blank lines at all, and imported that way every consecutive paragraph fuses into one, a paragraph next to a list is swallowed into the list item above it, a list beginning `1.` silently continues the previous list instead of starting its own, and two separate blockquotes fuse into one (or into one paragraph inside it). The script decides per adjacent pair rather than per file, so a source that has blank lines in some places and not others — around its images but not its paragraphs, say — is repaired everywhere it needs to be. A file that is already well-formed has no adjacent block lines to act on and comes through byte-identical. Where two paragraph lines meet, the line above is what decides: ending on sentence-final punctuation means two blocks, breaking mid-sentence means one soft-wrapped block, counted in `soft_wrapped_lines` — except a line that is only a bold span, like `**使用**` or `**安装**`, which reads as a heading-like label and always starts (or ends) a block on its own, regardless of punctuation. Two quote lines follow the same logic, with one exception: a bare `>` on either side is markdown's own idiom for a paragraph break *inside* one blockquote, and keeps them glued as a single block.

**Why the Zhihu file's tables are converted** (`--platform Zhihu` / `--platform all` only). `notion-fetch` returns tables as raw `<table>` HTML, marking the header with an attribute rather than `<th>`, and Zhihu's importer renders that header as an ordinary row. A pipe table's delimiter row is what makes Zhihu emit a real header. A table marked `header-row="false"` stays HTML, since a pipe table cannot be headerless.

**Why the Zhihu file's lists get flattened** (`--platform Zhihu` / `--platform all` only). Zhihu's editor is Draft.js, which holds a flat run of blocks, with no `<ol start>` and no way to nest a block inside a list item. Any block that interrupts a run of list items — nested bullets, a sub-paragraph, a code block — closes the list, and the items after it open a **new** list that restarts at 1. The script therefore folds each item's nested content into the item itself using markdown hard breaks, which survive the import as line breaks inside that one item. Nested markers are demoted (`- ` → `• `, `1. ` → `1）`) so they aren't re-parsed as a nested list.

**The Zhihu file's quotes** (`--platform Zhihu` / `--platform all` only). Two shapes are rewritten as HTML:
- Two or more one-line quotes in a row, with only blank lines between them, become consecutive `<blockquote>…</blockquote>` lines with no blank lines between: `> 甲` / `> ` / blank / `> 乙` / `> ` → `<blockquote>甲</blockquote>` / `<blockquote>乙</blockquote>`. A one-line quote standing alone keeps its markdown form, `> text` followed by a `> ` line.
- A quote holding only a numbered list becomes a `>` line followed by one `<li>…</li>` line per item, number kept inside: `> 1. 甲` → `<li>1. 甲</li>`. No `>` line closes it.

Other quotes — with several paragraphs, a bulleted list, or text and a list mixed — are left as they are.

**The Weixin file's numbered items** (`--platform Weixin` / `--platform all` only). Each numbered list item at the top level becomes one line wrapped in `<li></li>`, its number and markdown kept inside: `1. 用户原话型。` → `<li>1. 用户原话型。</li>`. Numbered items inside a quote, nested numbered items and bulleted items are left as they are. An item with indented lines under it is wrapped on its own line only, and a warning names it — those lines are no longer part of a markdown list once the item is HTML.

If `errors` is non-empty, stop and report exactly which images failed to download before continuing — a silently-dropped image is not acceptable. If `images` is empty, or `--image-hosting` is `no`, skip Steps 3.2 and 3.3 and go to Step 4.

#### Step 3.2 — Host every image in one batch per host list (`qingyun-file-hosting`)

The host list depends on the platform. Each output's `excluded_hosts` names the hosts whose links its platform cannot show — the Weixin file excludes `sxcu` and `uguu`, which WeChat does not accept; the unspecified and Zhihu files exclude nothing. So there is one upload for the outputs with an empty `excluded_hosts`, over the full host queue, and one more for each output that excludes hosts. Under `--platform all` that is two uploads: one for the unspecified and Zhihu files, which keep every host, and one for the Weixin file.

For each upload, run the `qingyun-file-hosting` skill — through the agent's skill mechanism, or by reading its `SKILL.md` and following its workflow — on **every** `local_path` in the manifest's `images[]`, **in manifest order, in a single invocation**, with `--persistence <value>` from Step 1 (omit it at `temporary`):
- **Outputs with no excluded hosts** (skip if there are none, as with `--platform Weixin`): leave its other options at their defaults. Send stdout to `<out-dir>/hosted-urls.json` — the folder that holds `manifest.json`.
- **Each output with excluded hosts** (currently `weixin`): add `--exclude <its excluded_hosts, comma-separated>`, i.e. `--exclude sxcu,uguu`. Send stdout to `<out-dir>/hosted-urls-<variant>.json`.

Keep each upload's stderr to read which provider took each image. Finalize each upload (Step 3.3) as soon as it finishes.

One batch, not one invocation per image: the host skill drops a provider that fails for the rest of its pass, so one dead or blocked host costs a single timeout for the whole article instead of one per image, and its rate-limit spill-over (picrd, scdn, sxcu) and proxy-bypassing retry lap are planned across every image at once. Its stdout keeps input order with `null` for each file that failed, which is exactly what Step 3.3 maps back onto the placeholders.

An exit status of `1` from the host skill means some images failed; carry on to Step 3.3, which leaves those images as placeholders. Any other non-zero status means nothing was uploaded: report its error and stop.

#### Step 3.3 — Swap in the hosted URLs (script)

Run, for the full-queue upload:
```
python3 qingyun-process-md/scripts/script.py finalize --manifest <manifest-path> --urls-file <out-dir>/hosted-urls.json
```
and for each output with excluded hosts:
```
python3 qingyun-process-md/scripts/script.py finalize --manifest <manifest-path> --urls-file <out-dir>/hosted-urls-<variant>.json --variants <variant>
```
Without `--variants`, it updates every output with no excluded hosts; with it, only the outputs named. It replaces each hosted image's placeholder with `![](<url>)` in those files, keeps the placeholder for each image that has no URL, recomputes each file's `expected_structure`, rewrites the files and `manifest.json`, and prints the updated manifest. Each output records its own links in `outputs[].images[]`; the top-level `images[]` mirrors the outputs with no excluded hosts (or the Weixin file, when it is the only one). It aborts if the number of URLs doesn't match the number of images still holding a placeholder in those files — re-run that upload on exactly those images, in manifest order, in that case. The same holds for retrying images that failed: run that upload again on just the images whose `placeholder` is still set in those files, then this step again with the same `--variants`.

Relay any `warnings`: those under an output name list content the script could not flatten in that file, so that list will still break where the warning says; the top-level ones name every image that could not be hosted, and for which files, which keeps its `【IMG-N】` placeholder there for inserting by hand after import from its `local_path`.

### Step 4 — Deliver

Copy each output's `processed_markdown` to `<output-dir>/<title>-<variant>.md` — `<title>-unspecified.md` for the `unspecified` output, `<title>-zhihu.md` for the `zhihu` one, `<title>-weixin.md` for the `weixin` one — creating `--output-dir` if needed. Sanitize `title` into a safe filename; if a file of that name already exists there, ask before overwriting it rather than silently replacing it. Report each destination path, then — unless `--image-hosting` is `no`, in which case say every image kept its placeholder — relay what Step 3.2 reported about hosting, as `qingyun-file-hosting`'s own report step lays out, separately for the Weixin file when it had its own upload: each image's provider and, for a temporary host, when its link expires, and any image that failed with its error and its `local_path`.

## Output

```
<output-dir>/                # ~/Downloads/processed-mds/ by default
├── <title>-unspecified.md   # --platform all / unspecified / RedNote
├── <title>-zhihu.md         # --platform all / Zhihu
└── <title>-weixin.md        # --platform all / Weixin
```
Each is the article body — without its title heading, except for a Notion source, whose first line is the page title (`# <title>`) — every hosted image as `![](<url>)` on its own paragraph, and `【IMG-N】` in place of each image that could not be hosted.

The working folder stays next to the source:
```
<source-name>-processed/
├── unspecified.md      # same content as <title>-unspecified.md, when written
├── zhihu.md            # same content as <title>-zhihu.md, when written
├── weixin.md           # same content as <title>-weixin.md, when written
├── manifest.json       # title, images (local_path, hosted_url / placeholder), per-output structure and warnings
├── hosted-urls.json    # qingyun-file-hosting's stdout, full host queue (absent with --image-hosting no)
├── hosted-urls-weixin.json   # its stdout for the Weixin file, without sxcu and uguu
└── images/
    ├── img-1.<ext>
    └── …
```
