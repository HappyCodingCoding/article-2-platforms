#!/usr/bin/env python3
"""Main script for the qingyun-md-2-zhihu skill: prepares a local markdown
file for import into Zhihu's column-article editor.

Usage:
    python3 script.py --source <path-to-local-markdown.md> [--title "..."] [--out-dir <dir>]

What it does:
    1. Reads the markdown file from disk (it must already be local -- if the
       source was a Notion page or another online link, fetch/download it to
       disk first, see SKILL.md Step 1).
    2. Finds the first heading and uses it as the article title (unless
       --title overrides this), and removes that heading line from the body
       so it is not duplicated once Zhihu's own title field is filled in.
    3. Finds every image reference in the body, in document order. A remote
       (http/https) image is downloaded immediately; a local/relative image
       path is copied in. Each image is saved as images/img-N.<ext> next to
       the processed markdown file.
    4. Replaces every image reference with a plain-text placeholder
       (【ZHIHU-IMG-N】) on its own paragraph, so the placeholder survives
       Zhihu's markdown-to-HTML import as an isolated, easy-to-find text node
       that can be swapped for the real uploaded image afterward.
    5. Rewrites raw <table> HTML as a markdown pipe table, so the first row
       becomes a real header, then normalizes block separation. Markdown
       separates blocks on a blank line, but some sources (`notion-fetch`
       among them) return one block per line with no blank lines, which fuses
       paragraphs, swallows them into neighbouring list items, and merges
       separate lists into one. The decision is made per adjacent pair, so a
       source separated in some places and not others is repaired everywhere
       it needs to be, and a well-formed file has nothing to act on.
    6. Flattens every list so each item is a single markdown block. Zhihu's
       editor is Draft.js, which has no <ol start> and no nested blocks
       inside a list item: any block that interrupts a run of list items
       (nested bullets, a sub-paragraph, a code block) ends the list, and
       the next item starts a brand new list numbered from 1 again. Nested
       content is folded into its parent item with markdown hard breaks so
       the run is never interrupted and the numbering stays continuous.
    7. Writes the processed markdown to <out-dir>/processed.md and prints a
       JSON manifest to stdout describing the title, the processed file,
       every image (its placeholder text and local path, in upload order),
       the block structure the import should produce, and any list content
       that could not be flattened safely.

This script never talks to Zhihu. Opening the editor, importing the file,
and inserting each image is done by the agent driving the browser, using
this manifest as its instructions.
"""

import argparse
import json
import mimetypes
import os
import re
import shutil
import ssl
import sys
import urllib.request
from urllib.parse import urlparse

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None  # fall back to the interpreter's own CA store

PLACEHOLDER_TMPL = "【ZHIHU-IMG-{n}】"

HEADING_RE = re.compile(r'^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$', re.MULTILINE)

# Matches either markdown image syntax or a raw <img> tag, in document order.
IMAGE_RE = re.compile(
    r'!\[[^\]]*\]\((?P<md_url>[^)\s]+)(?:\s+"[^"]*")?\)'
    r'|<img[^>]+src=["\'](?P<html_url>[^"\']+)["\'][^>]*/?>',
    re.IGNORECASE,
)

EXT_BY_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
}


def extract_title(text):
    """Return (title, text_with_heading_removed) for the first heading found.

    Returns (None, text) unchanged if no heading exists.
    """
    m = HEADING_RE.search(text)
    if not m:
        return None, text
    title = m.group(2).strip()
    start, end = m.span()
    # Also swallow one trailing newline so we don't leave a stray blank line.
    if end < len(text) and text[end] == "\n":
        end += 1
    new_text = text[:start] + text[end:]
    return title, new_text


def guess_ext(url, content_type=None):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext and len(ext) <= 5:
        return ext
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in EXT_BY_CONTENT_TYPE:
            return EXT_BY_CONTENT_TYPE[ct]
        guessed = mimetypes.guess_extension(ct)
        if guessed:
            return guessed
    return ".png"


def fetch_image(url, dest_no_ext, source_dir):
    """Download (http/https) or copy (local path) one image; return the
    final path actually written, including its extension."""
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (qingyun-md-2-zhihu)"})
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type")
        ext = guess_ext(url, content_type)
        dest = dest_no_ext + ext
        with open(dest, "wb") as fh:
            fh.write(data)
        return dest

    # Local path: resolve relative to the source markdown's own directory.
    local_path = url
    if parsed.scheme == "file":
        local_path = urllib.request.url2pathname(parsed.path)
    if not os.path.isabs(local_path):
        local_path = os.path.join(source_dir, local_path)
    local_path = os.path.normpath(local_path)
    if not os.path.isfile(local_path):
        raise FileNotFoundError("image not found on disk: %s" % local_path)
    ext = os.path.splitext(local_path)[1].lower() or ".png"
    dest = dest_no_ext + ext
    shutil.copyfile(local_path, dest)
    return dest


# --- List flattening -------------------------------------------------------
#
# Zhihu's editor is Draft.js. Its content model is a flat sequence of blocks,
# each with a type and a depth -- there is no <ol start> and no way to nest a
# block *inside* a list item. Its renderer numbers an ordered list by grouping
# consecutive ordered-list-item blocks, so ANY other block appearing between
# two items (a nested bullet list, a sub-paragraph, a code block) closes the
# list and the following items open a new one that restarts at 1.
#
# Markdown hard breaks survive the import as soft newlines *within* one list
# item, so folding nested content into its parent item keeps both the visual
# line structure and an unbroken run of items.

LIST_ITEM_RE = re.compile(
    r'^(?P<indent>[ \t]*)'
    r'(?P<marker>[-*+]|\d{1,9}[.)])'
    r'(?P<space>[ \t]+)'
    r'(?P<body>.*)$'
)

# A nested marker kept verbatim would be re-parsed as a nested list and break
# the run all over again, so it is rewritten to a look-alike that markdown
# does not treat as a list marker.
NESTED_BULLET_RE = re.compile(r'^[-*+][ \t]+')
NESTED_ORDERED_RE = re.compile(r'^(\d{1,9})[.)][ \t]+')

HARD_BREAK = "  "  # two trailing spaces: markdown's hard line break


def _is_blank(line):
    return not line.strip()


def _demote_nested_marker(line):
    """Turn a nested list marker into plain text that markdown ignores."""
    if NESTED_BULLET_RE.match(line):
        return NESTED_BULLET_RE.sub("\u2022 ", line)
    return NESTED_ORDERED_RE.sub(lambda m: m.group(1) + "\uff09", line)


# --- HTML tables ----------------------------------------------------------
#
# `notion-fetch` returns tables as raw <table> HTML, and Zhihu's importer does
# read that HTML — but it renders every cell as <td>, because Notion marks its
# header with an attribute (header-row="true") rather than with <th>. The
# result is a table with no header row: no shading, no bold. A markdown pipe
# table's delimiter row is what makes Zhihu emit <th>, so a table that wants a
# header is converted here, where the conversion is deterministic and Step 2
# can go on forbidding the agent from reformatting anything by hand.

HTML_TABLE_RE = re.compile(r'<table\b([^>]*)>(.*?)</table>', re.IGNORECASE | re.DOTALL)
HTML_ROW_RE = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.IGNORECASE | re.DOTALL)
HTML_CELL_RE = re.compile(r'<t[hd]\b[^>]*>(.*?)</t[hd]>', re.IGNORECASE | re.DOTALL)
HTML_LINK_RE = re.compile(r'<a\b[^>]*?href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
                          re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r'<[^>]+>')
HEADER_ROW_FALSE_RE = re.compile(r'header-row\s*=\s*["\']?false', re.IGNORECASE)

ENTITIES = [("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"),
            ("&quot;", '"'), ("&#39;", "'"), ("&amp;", "&")]


def _cell_text(html):
    """Flatten one cell to a single line, keeping its inline markup.

    Emphasis, code and links are carried across as markdown rather than
    stripped -- a cell's formatting is the author's content too.
    """
    text = re.sub(r'<br\s*/?>', ' ', html, flags=re.IGNORECASE)
    text = HTML_LINK_RE.sub(lambda m: '[%s](%s)' % (m.group(2).strip(), m.group(1)), text)
    text = re.sub(r'</?(strong|b)\b[^>]*>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(em|i)\b[^>]*>', '*', text, flags=re.IGNORECASE)
    text = re.sub(r'</?code\b[^>]*>', '`', text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub('', text)
    for entity, char in ENTITIES:
        text = text.replace(entity, char)
    return ' '.join(text.split()).replace('|', '\\|')


def convert_html_tables(text):
    """Rewrite each <table> that wants a header row as a markdown pipe table.

    A table explicitly marked header-row="false" is left as HTML: markdown
    has no way to write a headerless pipe table, so converting one would
    invent a header the source did not ask for.
    """

    def one_table(match):
        attrs, body = match.group(1), match.group(2)
        if HEADER_ROW_FALSE_RE.search(attrs):
            return match.group(0)

        rows = []
        for row_html in HTML_ROW_RE.findall(body):
            cells = [_cell_text(c) for c in HTML_CELL_RE.findall(row_html)]
            if cells:
                rows.append(cells)
        if len(rows) < 2:
            return match.group(0)  # nothing to gain, or nothing parseable

        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines = ["| " + " | ".join(rows[0]) + " |",
                 "| " + " | ".join(["---"] * width) + " |"]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n\n" + "\n".join(lines) + "\n\n"

    return HTML_TABLE_RE.sub(one_table, text)


# --- Source normalization -------------------------------------------------
#
# Markdown separates blocks on a BLANK line; a single newline is only a soft
# wrap. Some sources hand back one block per line with no blank lines at all
# (`notion-fetch` does), and imported as-is every consecutive paragraph fuses,
# a paragraph touching a list is absorbed into the preceding list item as lazy
# continuation, and an ordered list beginning with "1." silently continues the
# list above it instead of starting its own.
#
# A well-formed markdown file already has those blank lines, so it has no
# adjacent non-blank lines for this pass to act on and comes through untouched.
# The decision is made per adjacent pair rather than per document: a source can
# be separated in some places and not others, and only the pairs that markdown
# would actually merge need a blank line inserted between them.

FENCE_LINE_RE = re.compile(r'^\s*(```|~~~)')
TABLE_LINE_RE = re.compile(r'^\s*\|')
QUOTE_LINE_RE = re.compile(r'^\s*>')
HEADING_LINE_RE = re.compile(r'^\s*#{1,6}[ \t]')
HTML_OPEN_RE = re.compile(r'^\s*<([A-Za-z][A-Za-z0-9]*)')
# `Title` + `=====` (or `-----`) is a setext heading: the underline belongs to
# the line above it, and separating the two turns a heading into a paragraph
# followed by a horizontal rule.
SETEXT_RE = re.compile(r'^\s*(=+|-{2,})\s*$')


# Two paragraph lines in a row are either two blocks written without the blank
# line between them, or one paragraph the author soft-wrapped. A soft-wrapped
# line breaks mid-sentence, so a preceding line that ends on sentence-final
# punctuation marks the end of a block.
SENTENCE_END = "。．.！？!?…：:；;”』」）)"


def ends_a_sentence(line):
    """True when this line reads as the end of a block, not a soft wrap."""
    return line.rstrip().endswith(tuple(SENTENCE_END))


def line_kind(line):
    """Classify one line by the kind of block it starts."""
    if not line.strip():
        return "blank"
    if TABLE_LINE_RE.match(line):
        return "table"
    if SETEXT_RE.match(line):
        return "setext"
    if HTML_OPEN_RE.match(line):
        return "html"
    if QUOTE_LINE_RE.match(line):
        return "quote"
    if HEADING_LINE_RE.match(line):
        return "heading"
    m = LIST_ITEM_RE.match(line)
    if m and not m.group("indent"):
        return "list"
    if line[:1] in (" ", "\t"):
        return "indented"  # continuation of whatever block came before
    return "para"


# Runs of these belong to a single block, so consecutive lines of the same
# kind must stay glued together.
RUN_KINDS = {"table", "quote", "list", "html"}

# Kinds that must never be separated from the line above them, because they
# are part of that line's block rather than the start of a new one.
GLUED_KINDS = {"indented", "setext"}


def normalize_source(text):
    """Insert the blank lines markdown needs between adjacent block lines.

    Returns (text, inserted, soft_wraps): how many blank lines were added,
    and how many paragraph pairs were left alone as soft wrapping.

    A well-formed file has no adjacent non-blank lines to act on, so it comes
    through unchanged. Leading tabs are expanded either way: outside a fence a
    tab-indented line imports as a <pre> code block, which is never what the
    source meant.
    """
    out = []
    in_fence = False
    prev_kind = None
    prev_line = ""
    inserted = 0
    soft_wraps = 0

    for raw in text.split("\n"):
        if FENCE_LINE_RE.match(raw):
            in_fence = not in_fence
            out.append(raw)
            prev_kind = "fence"
            continue
        if in_fence:
            out.append(raw)  # fence contents are literal, tabs included
            continue

        line = raw.expandtabs(4)
        kind = line_kind(line)

        if prev_kind not in (None, "blank", "fence") and kind != "blank":
            same_run = kind == prev_kind and kind in RUN_KINDS
            # An html run holds whatever it contains, tag lines or not, until
            # the source itself ends it with a blank line.
            inside_html = prev_kind == "html"
            if inside_html:
                kind = "html"  # keep the run open across its text lines
            elif kind in GLUED_KINDS or same_run:
                pass  # part of the block above, never separated from it
            elif kind == "para" and prev_kind == "para":
                # The only ambiguous pair: two blocks, or one soft-wrapped one.
                if ends_a_sentence(prev_line):
                    out.append("")
                    inserted += 1
                else:
                    soft_wraps += 1
            else:
                out.append("")
                inserted += 1

        out.append(line)
        prev_kind = kind
        prev_line = line

    return "\n".join(out), inserted, soft_wraps


# --- Structure description ------------------------------------------------
#
# What the processed markdown says the imported article should look like.
# The agent checks the editor against this after importing (SKILL.md Step 7),
# so a source shape this script mis-handles stops the run instead of quietly
# producing a mangled draft.

def describe_structure(text):
    """Count the blocks the processed markdown should produce."""
    lists = []
    tables = []
    paragraphs = 0
    blockquotes = 0
    headings = 0

    lines = text.split("\n")
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if FENCE_LINE_RE.match(line):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence or not line.strip():
            i += 1
            continue

        kind = line_kind(line)
        if kind == "heading":
            headings += 1
            i += 1
        elif kind == "table":
            rows = 0
            while i < len(lines) and TABLE_LINE_RE.match(lines[i]):
                rows += 1
                i += 1
            # The |---|---| delimiter row is markup, not a rendered row.
            tables.append({"rows": max(rows - 1, 0)})
        elif kind == "html":
            rows = 0
            is_table = False
            while i < len(lines) and lines[i].strip():
                if re.search(r'<table\b', lines[i], re.IGNORECASE):
                    is_table = True
                if re.search(r'<tr\b', lines[i], re.IGNORECASE):
                    rows += 1
                i += 1
            if is_table:
                tables.append({"rows": rows})
            else:
                paragraphs += 1
        elif kind == "quote":
            while i < len(lines) and (QUOTE_LINE_RE.match(lines[i])
                                      or lines[i].startswith(" ")):
                i += 1
            blockquotes += 1
        elif kind == "list":
            items = 0
            ordered = bool(re.match(r'^\d', line.strip()))
            while i < len(lines) and lines[i].strip():
                m = LIST_ITEM_RE.match(lines[i])
                if m and not m.group("indent"):
                    items += 1
                elif not lines[i].startswith(" "):
                    break  # not an item and not a continuation: run is over
                i += 1
            lists.append({"type": "ol" if ordered else "ul", "items": items})
        else:
            while i < len(lines) and lines[i].strip() and \
                    line_kind(lines[i]) in ("para", "indented"):
                i += 1
            paragraphs += 1

    return {
        "paragraphs": paragraphs,
        "headings": headings,
        "blockquotes": blockquotes,
        "lists": lists,
        "tables": tables,
    }


def flatten_lists(text):
    """Fold each list item's nested content into the item itself.

    Returns (flattened_text, warnings). A warning is recorded when a list
    holds an image: an image has to stay its own block, so that list really
    does break there and the items after it restart their numbering.
    """
    lines = text.split("\n")
    out = []
    warnings = []
    i = 0

    def warn(line):
        warnings.append(
            "an image inside a list breaks the list there, so the items "
            "after it restart at 1: %s" % line.strip()[:80])

    while i < len(lines):
        m = LIST_ITEM_RE.match(lines[i])
        if not m or m.group("indent"):
            # Not the start of a top-level list item -- copy it through.
            out.append(lines[i])
            i += 1
            continue

        # A top-level list run: consume its items, folding each item's
        # nested content into the item, until a line ends the run.
        while i < len(lines):
            m = LIST_ITEM_RE.match(lines[i])
            if not m or m.group("indent"):
                break

            item_line = lines[i]
            if IMAGE_RE.search(item_line):
                warn(item_line)
            # Continuation lines must sit at the item's content column so
            # markdown reads them as part of this item, not as a new block.
            content_col = " " * (len(m.group("marker")) + len(m.group("space")))
            folded = []
            i += 1

            # Collect this item's nested and continuation lines. Blank lines
            # between them are dropped -- a blank line would end the block.
            blanks = 0
            run_continues = False
            while i < len(lines):
                line = lines[i].expandtabs(4)
                if _is_blank(line):
                    blanks += 1
                    i += 1
                    continue
                nested = LIST_ITEM_RE.match(line)
                if nested and not nested.group("indent"):
                    run_continues = True  # the next item of this same list
                    break
                if not line.startswith(" "):
                    break  # back to top level: the list run is over
                if IMAGE_RE.search(line):
                    warn(line)
                    break
                folded.append(_demote_nested_marker(line.strip()))
                blanks = 0
                i += 1

            if folded:
                item_line = (item_line.rstrip() + HARD_BREAK + "\n"
                             + (HARD_BREAK + "\n").join(
                                 content_col + f for f in folded))
            out.append(item_line)

            if not run_continues:
                # Give back the blank lines that trail the run, so the list
                # stays separated from whatever follows it.
                i -= blanks
                break

    return "\n".join(out), warnings


def process(source_path, out_dir, title_override=None):
    source_path = os.path.abspath(source_path)
    source_dir = os.path.dirname(source_path)

    with open(source_path, encoding="utf-8") as fh:
        text = fh.read()

    text = convert_html_tables(text)
    text, blanks_inserted, soft_wraps = normalize_source(text)

    if title_override:
        title = title_override
    else:
        title, text = extract_title(text)
        if title is None:
            raise SystemExit(
                "No title: the source has no '# ' heading and --title was "
                "not given. Zhihu never fills the title in from the body, so "
                "importing now would leave the draft untitled. Pass --title "
                "explicitly (for a Notion source, its properties.title).")
    if not title.strip():
        raise SystemExit("The title is empty; refusing to import an "
                         "untitled draft.")

    os.makedirs(out_dir, exist_ok=True)
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    images = []
    errors = []
    seen = [0]  # images encountered, including ones that failed to download

    def replace(match):
        seen[0] += 1
        idx = seen[0]
        url = match.group("md_url") or match.group("html_url")
        placeholder = PLACEHOLDER_TMPL.format(n=idx)
        dest_no_ext = os.path.join(images_dir, "img-%d" % idx)
        try:
            local_path = fetch_image(url, dest_no_ext, source_dir)
        except Exception as exc:  # noqa: BLE001 - report, don't abort the run
            errors.append({"index": idx, "source_url": url, "error": str(exc)})
            return match.group(0)  # leave the original markdown untouched
        images.append({
            "index": idx,
            "placeholder": placeholder,
            "source_url": url,
            "local_path": os.path.abspath(local_path),
        })
        # Isolate the placeholder on its own paragraph.
        return "\n\n%s\n\n" % placeholder

    text, warnings = flatten_lists(text)
    processed_text = IMAGE_RE.sub(replace, text)
    structure = describe_structure(processed_text)
    structure["images"] = len(images)

    # Paragraph lines left joined because the line above them broke
    # mid-sentence. Usually right, but it is also what a genuinely merged
    # source looks like, so say so rather than deciding silently.
    if soft_wraps:
        warnings.append(
            "%d paragraph line(s) were treated as soft wrapping and left "
            "joined to the line above, because that line did not end on "
            "sentence-final punctuation. If the article reads as merged "
            "paragraphs, the source lost its blank lines before reaching "
            "this script." % soft_wraps)

    processed_path = os.path.join(out_dir, "processed.md")
    with open(processed_path, "w", encoding="utf-8") as fh:
        fh.write(processed_text)

    return {
        "title": title,
        "source": source_path,
        "processed_markdown": os.path.abspath(processed_path),
        "images_dir": os.path.abspath(images_dir),
        "images": images,
        "blank_lines_inserted": blanks_inserted,
        "soft_wrapped_lines": soft_wraps,
        "expected_structure": structure,
        "warnings": warnings,
        "errors": errors,
    }


def main():
    ap = argparse.ArgumentParser(
        description="qingyun-md-2-zhihu: prepare a local markdown file "
                     "(title + placeholder'd images) for Zhihu import")
    ap.add_argument("--source", required=True,
                     help="path to the local markdown file")
    ap.add_argument("--title", default=None,
                     help="override title instead of auto-detecting the "
                          "first heading")
    ap.add_argument("--out-dir", default=None,
                     help="where to write processed.md and images/ "
                          "(default: a sibling 'zhihu-import' folder next "
                          "to the source file)")
    args = ap.parse_args()

    if not os.path.isfile(args.source):
        raise SystemExit("source markdown not found: %s" % args.source)

    out_dir = args.out_dir
    if not out_dir:
        base = os.path.splitext(os.path.basename(args.source))[0]
        out_dir = os.path.join(os.path.dirname(os.path.abspath(args.source)),
                                base + "-zhihu-import")

    manifest = process(args.source, out_dir, args.title)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if manifest["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
