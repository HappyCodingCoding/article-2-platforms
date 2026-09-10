# Useful alternatives

Approaches that were tested and worked, but were still ruled out as the
skill's method for the step they apply to. Kept here instead of in
SKILL.md per this project's rule against carrying alternatives in a
skill's own instructions — SKILL.md should describe what the agent does,
not the options it considered.

## Image insertion (Step 8)

Both alternatives below were tried on an earlier, incorrect belief that
the dialog's file input couldn't be filled by automation (it can — see
`zhihu-editor-notes.md`, "上传"和"插入"是两件事"). They solve the same
problem — getting a local image into the editor — and share the same
weakness: both insert the image before its upload finishes, entirely
inside the editor, which is the window where an image can stall into
上传失败 if the next one starts too soon. The dialog flow SKILL.md
actually uses avoids that window: the image is already on Zhihu's CDN
by the time it's inserted. Everything specific to each mechanism follows.

### Clipboard paste

Put the image on the system clipboard, select the placeholder, send a
real paste keystroke:

```
osascript -e 'set the clipboard to (read (POSIX file "img-1.png") as «class PNGf»)'
```
then select the placeholder text and send `cmd+v`.

This inserts at the cursor and reaches the same `pic-private.zhihu.com`
CDN as the dialog flow — verified directly, not assumed. Ruled out as the
default because:

- The OS clipboard is shared, global state. Anything else running on the
  machine can overwrite it between the `osascript` call and the paste —
  observed in this session, where an unrelated action left the user's own
  chat text on the clipboard. A clobbered clipboard doesn't error, it
  silently pastes the wrong content.
- It destroys whatever the user had copied, as a side effect of a task
  unrelated to their clipboard.
- It's platform-specific (the `osascript` invocation is macOS-only).

Still a reasonable fallback if the dialog's file input ever becomes
unreachable (e.g. Zhihu redesigns the upload modal): select the
placeholder, re-copy the image immediately before each paste (never
copy all images up front), and wait for that image's `src` to become
`https://pic…` before moving to the next one.

### Local HTTP server + synthetic paste

Serve the images directory over `127.0.0.1`, then in page JS `fetch` each
image, wrap it in a `File`, put it in a `DataTransfer`, and dispatch a
synthetic paste:

```javascript
const r = await fetch('http://127.0.0.1:8899/img-1.png');
const dt = new DataTransfer();
dt.items.add(new File([await r.blob()], 'img-1.png', {type: 'image/png'}));
document.querySelector('.public-DraftEditor-content[contenteditable="true"]')
  .dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```

Also verified end to end — all 6 images in a test draft, correct
dimensions, correct order, on the CDN — once paced to wait for each
upload before starting the next. Ruled out as the default because:

- It needs page-JS execution for the insertion itself. The dialog flow
  only needs JS to locate the placeholder; the file-upload and click
  actions that actually place the image need no JS at all.
- It's an extra background process to start and tear down. A leaked
  server on the user's machine is a real, avoidable loose end.
- It depends on Chrome's Private Network Access policy continuing to
  allow an `https://` page to `fetch` `127.0.0.1`. That policy has been
  tightening across Chrome versions and could add a permission prompt or
  block it outright in a future release.

## List flattening (Step 3)

The problem: Zhihu's editor is Draft.js, whose content model is a flat run
of blocks with no `<ol start>` and no nested blocks inside a list item.
Any block interrupting a run of ordered-list items closes the list, and
the items after it start a new one numbered from 1. All four candidates
below were imported into a real draft in one test document and their
resulting DOM inspected; the numbers are what Zhihu actually produced,
not what the markdown spec predicts.

The chosen mechanism — markdown hard breaks (two trailing spaces) with
continuation lines aligned to the item's content column — produced a
single `ol` with every item intact and each nested line preserved as its
own line inside its parent item. It is plain markdown, so it carries no
dependency on Zhihu accepting inline HTML.

### `<br>` tags inside the list item

```
3. gamma<br>a) sub a<br>b) sub b
```

Produced exactly the same DOM as the hard-break form: one `ol`, sub-lines
as soft newlines within item 3. Ruled out only because it relies on
Zhihu's converter passing inline HTML through — an implementation detail
that is free to change, where a hard break is markdown's own construct
for the same thing. Worth reaching for if hard breaks ever stop working.

### Backslash-escaped numbers as plain paragraphs

```
7\. 给所有生成的标题打分
```

Degrades the whole list to ordinary paragraphs whose numbers are literal
text, so nothing can renumber them. The escape works — Zhihu renders
`7. …` with no stray backslash. Ruled out because it throws away the list
semantics for every list in the article, not just the one that would have
broken, and because it does nothing for the nested content itself: a
tab-indented line between two such paragraphs imports as a `<pre>` code
block.

### Plain continuation lines, no hard break

```
3. gamma
   a) sub a
   b) sub b
```

Keeps the list in one piece — one `ol`, all items — but markdown's lazy
continuation joins the nested lines onto the parent's line with spaces,
so a four-step sub-list collapses into one long run-on line. Correct
numbering, wrong shape.

### Leaving the nesting alone and repairing the DOM after import

Not tested, and not worth testing: Draft.js rebuilds its DOM from its own
`ContentState`, so an `ol` given a `start` attribute (or blocks stitched
together) by hand is discarded at the next keystroke or autosave, and the
draft that reaches the server is the unrepaired one. The content has to be
correct in the markdown handed to `document/convert`.

## Getting a faithful copy of a Notion page (Step 2)

`notion-fetch` returns the page as text into the agent's context, so the
article reaches disk only by being retyped through the agent's own output.
Measured against a manual Notion export of the same page, two separate runs
each lost something different: one dropped 40 blank lines, the page title and
20 curly quotes; the other dropped two inline links. The normalization in
Step 3 repairs the structural half of this deterministically, but character
fidelity still rests on Step 2's copying rules.

### Exporting the .md from Notion through the browser

Notion's own ••• → Export → Markdown & CSV writes a `.zip` to disk via the
Chrome session the skill already opens, so the article text never passes
through the agent at all. It would also make the images local files inside
the zip, removing the presigned-URL expiry race and the requirement that
Steps 2 and 3 run back to back.

Set aside, not disproven — it was never tested. Against it: it is a file
download, so it needs the user's explicit approval on every run rather than
happening quietly; the export is async and arrives by email for large pages;
the menu path is more fragile than a tool call; and the zip has to be
unpacked and the `.md` located inside a folder Notion names after the page
title plus a hash. Worth revisiting if transcription fidelity turns out to
matter more than those costs.

### Other Notion MCP tools

Checked and ruled out — none of them export a page to a file.
`download-attachment` reads only attachments the integration itself created
with `create-attachment`, caps at 200 KiB, and returns the text in the
response (so it lands in context anyway); `create-file-upload` uploads *to*
Notion; nothing in the `duplicate-page` / `update-page` / query / search
families exports. `fetch` is the only read path.

## Locating a file input (Steps 5 and 8)

### Describing it to `find`

The obvious approach, and the one that fails. `find` and `read_page` match on
an element's role, name and surrounding text, not on its attributes, and the
Zhihu editor carries four file inputs whose descriptions overlap: the 附件
attachment input (`.pdf,.md,.txt,…,.png,.jpg`), the image dialog's
(`image/webp,image/jpg,…`), the article-cover input (`.jpeg, .jpg, .png`) and
the MD/Doc import input (`.docx,.markdown,…`). Asking for "the image input"
or "the markdown input" returns whichever the description happens to fit —
observed in a real run: an image uploaded to the attachment input, which
turns the dialog's button into 添加文件 and inserts a file-name card rather
than a picture, with no error anywhere.

Ruled out in favour of selecting by `accept` in page JS, stamping the winner
with a unique `aria-label`, and searching for that label — which is exact,
and prints the `accept` it chose so the decision is visible before anything
is uploaded.

## Getting the upload dialog to react (Step 8)

### Dispatching the `change` event by hand

Tried in a real run and ruled out. The file-upload tool fires the input's
change handler itself; the dialog is merely slow to show 已上传 N 张图片, which
reads like nothing happened. Dispatching a `change` event in page JS to nudge
it makes the handler run a second time, and the image is inserted twice.

The duplicate is cheap to clean up — the figure's hover **×** removes it, and
the neighbour check catches it immediately — but the fix is to wait and read
the dialog again. Later images in that same run went in cleanly with no
dispatch at all.

## Recovering from a misplaced image (Step 8)

### Undo, then retry the same placeholder

Tried in a real run and ruled out. The placeholder is deleted before the
upload begins, so by the time an insert goes wrong the anchor is already
gone; Draft.js's undo restores the text of the block but not the caret, and
the retry then inserts at whatever the cursor drifted to. In that run image 1
ended up after the first paragraph instead of the fourth, and every check
that existed at the time — image count, CDN src, no placeholders remaining,
server `state: draft` — passed.

The skill rebuilds instead: clear the body, re-import, run the loop again.
Consistent with the existing rule that a draft in a bad state is easier to
rebuild than to repair.

## Deciding when to insert missing blank lines (Step 3)

The normalizer must not split paragraphs an author soft-wrapped, so it has to
tell a missing block separator from a deliberate line break. It decides per
adjacent pair: cross-kind pairs (paragraph next to list, quote, table or
heading) always get a blank line, and where two paragraph lines meet, the line
above decides — ending on sentence-final punctuation means two blocks,
breaking mid-sentence means one soft-wrapped block.

### A whole-document blank-line density test

The first version measured the ratio of blank to non-blank lines and skipped
the pass entirely on any file above 5%, reasoning that a real markdown article
separates its blocks and a dump does not. Measured 4% on a `notion-fetch`
dump and 28–34% on two well-formed files, which looked like a wide margin.

Ruled out after it failed on a real run. A source is not uniformly one shape:
that run's file carried blank lines around its **images** but not between its
**paragraphs** — 19 blank lines against 169 non-blank, 11.2%, over the gate —
so the pass was skipped wholesale and all 35 paragraphs imported as 20. The
flaw is the shape of the test, not the constant: damage happens per adjacent
pair, so a single global verdict is either too coarse for a half-separated
file or too eager for a soft-wrapped one, and no threshold fixes both. Judging
each pair on its own removes the constant altogether, and makes the pass a
provable no-op on a well-formed file — it has no adjacent block lines to act
on, so it returns the input byte-for-byte.

### An explicit `--source-format notion` flag instead

Rejected despite being more direct. The flag would have to be set by the
agent, which puts the correctness of every import back into a decision a
model makes per run — the exact failure this whole change exists to remove.
A file the script measures for itself behaves the same no matter who invoked
it. The flag would also be wrong whenever a *local* file happens to be a
saved `notion-fetch` dump, which the density test handles on its own.

## Passing Notion's raw `<table>` HTML straight through (Step 3)

`notion-fetch` returns tables as raw `<table>` HTML, and Zhihu's importer does
parse it — so leaving it alone looks like the lower-interference choice, and
was tried.

Ruled out. Zhihu renders that HTML with **no header row**: Notion marks its
header with an attribute (`header-row="true"`) and uses `<td>` for every cell,
never `<th>`, and Zhihu goes by the tag. A markdown pipe table's delimiter row
is what makes it emit `<th>`. Measured on one imported document holding the
same table both ways:

| Source | Header cells | Header background | Font weight |
| --- | --- | --- | --- |
| pipe table | `<th>` × 3 | `rgb(235,236,237)` | 500 |
| raw `<table>` HTML | none, all `<td>` | transparent | 400 |

Row and cell counts are identical between the two, and so is the outer
`<table>` element — which is why an earlier check that compared only those
concluded, wrongly, that the two were equivalent. The difference is `th` vs
`td`, and it is plainly visible in the editor.

A table explicitly marked `header-row="false"` *is* still passed through as
HTML: markdown cannot express a headerless pipe table, so converting one
would invent a header the source never asked for.

Note that Zhihu flattens inline formatting inside table cells either way —
`**bold**` and `[text](url)` in a cell render as plain text. The converter
carries that markup across rather than stripping it, but nothing visible
depends on it.

## Known limits of the Step 3 normalization

Recorded so they are not rediscovered as surprises.

- **The 5% density threshold is empirical**, measured on three real files
  (4%, 28%, 34%). The margin is wide, but a half-normalized document sitting
  near the boundary has never been tested.
- **`flatten_lists` only handles top-level lists.** A list written inside a
  blockquote (`> 1. item`) is classified as quote content and left alone, and
  a list nested two levels deep is not flattened.
- **An image inside a list item is reported, not repaired.** It has to stay
  its own block, so that list genuinely does break there.
- **Only `<table>` is recognised among HTML blocks.** Other block-level HTML
  survives the blank-line pass intact but is counted as a paragraph.
- **Step 7's DOM mapping was verified against one article's block shapes.**
  Headings are counted by the script but not compared, because this skill
  strips the article's only heading to use as the title.
