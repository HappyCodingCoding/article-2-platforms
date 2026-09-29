# Useful alternatives

Approaches that work but were ruled out as the skill's method for the step
they apply to.

## Hosting the images (Step 3)

### One `qingyun-file-hosting` invocation per image

Works, and gives the simplest mapping from image to URL: one invocation, one
bare URL. Ruled out because each invocation starts with a fresh fallback
queue. A provider that is down or blocked from this machine is then retried
for every image, each time costing a full request timeout (25 s and up) before
the image moves on, and the host skill's rate-limit spill-over and
proxy-bypassing retry lap are planned per image instead of across the article.
A single batch invocation drops a failing provider once for the whole pass and
still returns URLs in input order, with `null` marking each failure, so the
mapping stays exact.

### Calling `qingyun-file-hosting`'s script from this skill's script

`script.py` could run `../../qingyun-file-hosting/scripts/script.py` itself as
a subprocess, making Step 3 one command instead of three. Ruled out because it
bypasses the host skill's own workflow — its option checks, its ImgBB key
prompt, and its report of each image's provider and expiry, which would have
to be re-parsed from stderr — and ties this script to the two skills sitting
side by side on disk.

### Uploading straight to img.scdn.io

Uploading each image file from disk to img.scdn.io from this skill's own
script, in a multipart `image` field, asking for the source's own
`outputFormat` and leaving `cdn_domain` unset. Works, with no second skill
involved, and is the one host Zhihu's import has been verified to re-host
from: it copied the resulting URLs onto `pic-private.zhihu.com` at the right
positions and sizes. Ruled out because it is one host with no fallback: an
image it refuses or reworks (it reduces a PNG to 256 colours), one over its
size limit, or a network block from this machine leaves the image unhosted or
degraded, where `qingyun-file-hosting` moves it down a ranked queue of hosts
until one takes it. `--host scdn` on that skill still reaches it alone.

Variations of the upload itself, tried while it was the method:

#### Letting the host fetch the image itself (`image_url`)

The API accepts `image_url` and downloads the image server-side, which would
skip the local download. Ruled out: local files and relative paths have no URL
to hand it, so the script would need both paths anyway; the host fetches
through its own proxy, one more hop for a Notion link that is already racing
its ~5-minute expiry; and the manual fallback after import needs every image
on disk regardless.

#### Pinning a mainland CDN (`cdn_domain=esaimg.cdn1.vip`)

Tested and worked: the upload returned an `esaimg.cdn1.vip` URL, and Zhihu
re-hosted it exactly like the default. Not chosen because the default worked
just as well, and the host's CDN list moves — the default upload returned
`img.cdn1.vip`, which is not on the documented list at all — so a pinned
domain is one more thing that can go stale.

#### The host's default `outputFormat=auto`

Converts static images to WebP. Not tested against Zhihu's importer. Ruled out
because requesting the source's own format keeps the image as the author
supplied it, and Zhihu recompresses it on its own CDN anyway.

## Getting a faithful copy of a Notion page (Step 2)

`notion-fetch` returns the page as text into the agent's context, so the
article reaches disk only by being retyped through the agent's own output.
Measured against a manual Notion export of the same page, two separate runs
each lost something different: one dropped 40 blank lines, the page title and
20 curly quotes; the other dropped two inline links. The normalization in
Step 3.1 repairs the structural half of this deterministically, but character
fidelity still rests on Step 2's copying rules.

The chosen mechanism takes `notion-fetch`'s Notion-flavored markdown as it is
and converts it with a script (`scripts/notion_md.py`) into the markdown the
Notion app's Export → Markdown writes. Checked byte for byte against a real
export of one article (image targets aside, which are local paths in the
export and signed URLs here).

### Reading the fetched markdown as standard markdown

What the skill first did. Ruled out after a real run: a list inside a quote
became a code block outside it, every quote lost the closing `> ` line the
export writes, `~` stayed escaped as `\~`, and `<empty-block/>` survived as
literal text. Notion-flavored markdown only looks like standard markdown; its
nesting, escaping and block separation follow its own spec.

### Notion's `GET /v1/pages/{page_id}/markdown` endpoint

The official API's markdown endpoint. Ruled out: it returns the same
Notion-flavored markdown `notion-fetch` does, so it would need the same
conversion, and it needs an API token besides — and its read endpoint is
restricted to public integrations.

### The official block API (`GET /v1/blocks/{id}/children`)

Returns every block as JSON with its rich text unescaped, so nothing has to be
parsed out of a text format. Not chosen: it needs the user to create a Notion
integration, keep its token on this machine and share every page with it, and
the JSON still has to be serialized into export-style markdown — the same
rendering rules the chosen converter already applies. Worth revisiting if
Notion-flavored markdown ever turns out to lose information the export keeps.

### Asking the user to export the page themselves

Byte-identical to the export by definition, with images as local files, so
there is no presigned-URL race. Ruled out because every Notion article would
need a manual export, unzip and path hand-off before the skill can start.

### Exporting the .md from Notion through the browser

Notion's own ••• → Export → Markdown & CSV writes a `.zip` to disk via the
Chrome session the skill already opens, so the article text never passes
through the agent at all. It would also make the images local files inside
the zip, removing the presigned-URL expiry race and the requirement that
Steps 2 and 3.1 run back to back.

Ruled out, never tested: it is a file download, so it needs the user's
explicit approval on every run rather than happening quietly; the export is
async and arrives by email for large pages; the menu path is more fragile than
a tool call; and the zip has to be unpacked and the `.md` located inside a
folder Notion names after the page title plus a hash.

### Other Notion MCP tools

Checked and ruled out — none of them export a page to a file.
`download-attachment` reads only attachments the integration itself created
with `create-attachment`, caps at 200 KiB, and returns the text in the
response (so it lands in context anyway); `create-file-upload` uploads *to*
Notion; nothing in the `duplicate-page` / `update-page` / query / search
families exports. `fetch` is the only read path.

## List flattening (Step 3.1, `--platform Zhihu`)

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

## Deciding when to insert missing blank lines (Step 3.1)

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

## Passing Notion's raw `<table>` HTML straight through to Zhihu (Step 3.1, `--platform Zhihu`)

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

## Known limits of the Step 3.1 normalization

Recorded so they are not rediscovered as surprises.

- **`flatten_lists` only handles top-level lists.** A list written inside a
  blockquote (`> 1. item`) is classified as quote content and left alone, and
  a list nested two levels deep is not flattened.
- **An image inside a list item is reported, not repaired.** It has to stay
  its own block, so that list genuinely does break there.
- **Only `<table>` is recognised among HTML blocks.** Other block-level HTML
  survives the blank-line pass intact but is counted as a paragraph.
- **An html run ends at its opening element's closing tag.** An element whose
  closing tag sits on the same line as a nested element's, or one that is
  never closed, is judged by that first closing tag or runs to the next blank
  line.
