#!/usr/bin/env python3
"""Main script for the qingyun-process-md skill: turns a local markdown
article into one whose images are public URLs, ready to import into a
Chinese social platform's editor.

Usage:
    python3 script.py notion --input <notion-fetch-content.md> --title "..." --output <article.md>
    python3 script.py prepare --source <path-to-local-markdown.md> [--platform unspecified|all|zhihu|weixin|rednote] [--title "..."] [--out-dir <dir>]
    python3 script.py finalize --manifest <out-dir>/manifest.json --urls-file <file> [--variants <v>[,<v>...]]

`notion` (Notion sources only, before `prepare`) turns the Notion-flavored
markdown `notion-fetch` returns into the markdown the Notion app's own
export writes, with the page title as its '# ' heading (see notion_md.py).

The rest of the work is split in two because image hosting belongs to
another skill, qingyun-file-hosting, which the agent runs between `prepare`
and `finalize` on every image at once.

`prepare` writes one output per variant that --platform asks for:
`unspecified.md` (for unspecified and rednote), `zhihu.md` (for zhihu) and
`weixin.md` (for weixin); all writes all three. Each variant is built from
the raw source:
    1. Reads the markdown file from disk (it must already be local -- if the
       source was a Notion page or another online link, fetch/download it to
       disk first, see SKILL.md Step 2).
    2. zhihu only: rewrites raw <table> HTML as a markdown pipe table, so the
       first row becomes a real header -- Zhihu's importer renders a Notion
       table's header row as an ordinary row.
    3. Normalizes block separation. Markdown separates blocks on a blank
       line, but some sources (`notion-fetch` among them) return one block
       per line with no blank lines, which fuses paragraphs, swallows them
       into neighbouring list items, merges separate lists into one, and
       merges separate blockquotes into one. The decision is made per
       adjacent pair, so a source separated in some places and not others is
       repaired everywhere it needs to be, and a well-formed file has nothing
       to act on.
    4. Finds the first heading and uses it as the article title (unless
       --title overrides this), and removes that heading line from the body
       so it is not duplicated once the platform's own title field is filled
       in.
    5. zhihu only: flattens every list so each item is a single markdown
       block. Zhihu's editor is Draft.js, which has no <ol start> and no
       nested blocks inside a list item: any block that interrupts a run of
       list items (nested bullets, a sub-paragraph, a code block) ends the
       list, and the next item starts a brand new list numbered from 1 again.
       Nested content is folded into its parent item with markdown hard
       breaks so the run is never interrupted and the numbering stays
       continuous.
       weixin only: wraps each top-level numbered list item -- not one inside
       a quote, not a nested or bulleted one -- in <li></li>.
    6. Finds every image reference in the body, in document order. A remote
       (http/https) image is downloaded immediately; a local/relative image
       path is copied in. Each image is saved once, as images/img-N.<ext>,
       and shared by every variant; each reference is replaced by a
       plain-text placeholder (【IMG-N】) on its own paragraph.
    7. Writes each variant to <out-dir>/<variant>.md, saves a JSON manifest
       to <out-dir>/manifest.json and prints it to stdout: the title, every
       image (its placeholder and local path, in document order), and per
       output its file, the block structure it should produce, and any list
       content that could not be flattened safely.

`finalize`:
    Reads the URLs qingyun-file-hosting printed for one upload -- a JSON
    array in image order with null for a failed upload, or a bare URL when
    there was one image -- swaps each hosted image's placeholder for a
    markdown image at its URL in the outputs that upload was for, and
    rewrites the outputs and manifest.json. An output whose platform cannot
    show some hosts' links (EXCLUDED_HOSTS: weixin excludes sxcu and uguu)
    gets its own upload without them, finalized with --variants; the other
    outputs share an upload over the full host queue, the default.
    An image that failed to upload keeps its placeholder, which a platform
    import keeps as an isolated, easy-to-find text node for inserting that
    image by hand.

This script never uploads anything and never talks to a platform.
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
from urllib.parse import unquote, urlparse

import notion_md

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None  # fall back to the interpreter's own CA store

PLACEHOLDER_TMPL = "【IMG-{n}】"

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
            url, headers={"User-Agent": "Mozilla/5.0 (qingyun-process-md)"})
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
        # Exporters (Notion's among them) percent-encode the relative path,
        # since a markdown link cannot hold spaces or most non-ASCII as-is.
        decoded = unquote(local_path)
        if not os.path.isfile(decoded):
            raise FileNotFoundError("image not found on disk: %s" % local_path)
        local_path = decoded
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
# continuation, an ordered list beginning with "1." silently continues the
# list above it instead of starting its own, and two separate blockquotes
# fuse into one (or into one paragraph inside it).
#
# A well-formed markdown file already has those blank lines, so it has no
# adjacent non-blank lines for this pass to act on and comes through untouched.
# The decision is made per adjacent pair rather than per document: a source can
# be separated in some places and not others, and only the pairs that markdown
# would actually merge need a blank line inserted between them.

FENCE_LINE_RE = re.compile(r'^\s*(```|~~~)')
TABLE_LINE_RE = re.compile(r'^\s*\|')
QUOTE_LINE_RE = re.compile(r'^\s*>')
# A quote marker with nothing after it (`>`, `> `, `>>` ...) -- markdown's
# idiom for a paragraph break *inside* one blockquote. Its presence is the
# only signal that two adjacent quote lines belong to the same block rather
# than being two blocks that simply landed next to each other.
EMPTY_QUOTE_RE = re.compile(r'^\s*(>[ \t]*)+$')
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

# A line that is nothing but one bold (or bold-underscore) span reads as a
# mini-heading/label -- "**使用**", "**安装**" -- never as the first half of a
# sentence that continues, soft-wrapped, on the next line. It is checked on
# both sides of a para/para pair: as the line above, it never blends into
# what follows; as the line below, it never continues what came before.
LABEL_LINE_RE = re.compile(r'^(\*\*|__)(?:(?!\1).)+\1\s*$')


def ends_a_sentence(line):
    """True when this line reads as the end of a block, not a soft wrap."""
    return line.rstrip().endswith(tuple(SENTENCE_END))


def is_label_line(line):
    """True for a line that is only a bold span, used as a heading-like label."""
    return bool(LABEL_LINE_RE.match(line.strip()))


QUOTE_MARKERS_RE = re.compile(r'^\s*(?:>[ ]?)+')


def is_quoted_list_line(line):
    """True for a quote line holding a list item, or an indented line under one.

    `notion-fetch` never writes these -- it puts a quote's children on
    tab-indented lines below it -- so a quote line like `> 2. item` comes from
    standard markdown, where it continues the list inside the quote above.
    """
    content = QUOTE_MARKERS_RE.sub("", line, count=1)
    return bool(LIST_ITEM_RE.match(content)) or content[:1] in (" ", "\t")


def is_empty_quote(line):
    """True for a quote-marker line carrying no text of its own."""
    return bool(EMPTY_QUOTE_RE.match(line))


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
# kind must stay glued together. Quote is deliberately not here: unlike a
# table's rows or a list's items, two adjacent quote lines are ambiguous --
# see the quote/quote branch below.
RUN_KINDS = {"table", "list", "html"}

# Kinds that must never be separated from the line above them, because they
# are part of that line's block rather than the start of a new one.
GLUED_KINDS = {"indented", "setext"}

# Elements that never take a closing tag, so an html run opened by one ends on
# its own line.
VOID_TAGS = {"area", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "source", "track", "wbr"}


def closes_html_run(tag, line):
    """True when this line ends the html run that `tag` opened.

    An html run ends at its element's closing tag -- `notion-fetch` puts the
    next block on the very next line, so waiting for a blank line would glue
    the rest of the article into the element.
    """
    if tag in VOID_TAGS:
        return True
    return re.search(r'</%s\s*>' % re.escape(tag), line, re.IGNORECASE) is not None


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
    html_tag = None  # the element an open html run is waiting to see closed
    block_kind = None  # the kind of line that opened the current block

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

        if kind == "blank":
            html_tag = None

        if prev_kind not in (None, "blank", "fence") and kind != "blank":
            # An html run holds whatever it contains, tag lines or not, until
            # its element closes or the source ends it with a blank line.
            inside_html = html_tag is not None
            if prev_kind == "html" and not inside_html:
                prev_kind = "html-closed"  # a finished element, not a run
            same_run = kind == prev_kind and kind in RUN_KINDS
            # The next item after a list item's nested content belongs to the
            # same list; a blank line there would make the whole list loose.
            if kind == "list" and prev_kind == "indented" and block_kind == "list":
                same_run = True
            if inside_html:
                kind = "html"  # keep the run open across its text lines
            elif kind in GLUED_KINDS or same_run:
                pass  # part of the block above, never separated from it
            elif kind == "para" and prev_kind == "para":
                # The only ambiguous pair: two blocks, or one soft-wrapped one.
                # A bold-only label line (a mini-heading like "**使用**") settles
                # it either way, regardless of how it or its neighbour end.
                if (ends_a_sentence(prev_line) or is_label_line(prev_line)
                        or is_label_line(line)):
                    out.append("")
                    inserted += 1
                else:
                    soft_wraps += 1
            elif kind == "quote" and prev_kind == "quote":
                # `notion-fetch` hands back one quote *block* per line, so two
                # quote lines with real content and no separator between them
                # are almost always two distinct blockquotes landing next to
                # each other -- left glued, they merge into one blockquote
                # (or one paragraph inside it). The one legitimate reason to
                # keep them glued is markdown's own idiom for a paragraph
                # break *inside* a single blockquote: a bare `>` line. Its
                # presence on either side means the author already marked
                # this pair as belonging to the same block. So does a list
                # item (or its indented continuation) inside the quote.
                if (is_empty_quote(prev_line) or is_empty_quote(line)
                        or is_quoted_list_line(line)):
                    pass
                else:
                    out.append("")
                    inserted += 1
            else:
                out.append("")
                inserted += 1

        if kind == "html":
            if html_tag is None:
                html_tag = HTML_OPEN_RE.match(line).group(1).lower()
            if closes_html_run(html_tag, line):
                html_tag = None

        if kind not in GLUED_KINDS:
            block_kind = kind

        out.append(line)
        prev_kind = kind
        prev_line = line

    return "\n".join(out), inserted, soft_wraps


# --- Structure description ------------------------------------------------
#
# What the processed markdown says the imported article should look like.
# A publishing skill checks the editor against this after importing, so a
# source shape this script mis-handles stops the run instead of quietly
# producing a mangled draft.

# A hosted image alone on its line imports as an image block, not a paragraph.
IMAGE_LINE_RE = re.compile(r'^!\[[^\]]*\]\([^)\s]+\)\s*$')


def describe_structure(text):
    """Count the blocks the processed markdown should produce."""
    lists = []
    tables = []
    paragraphs = 0
    blockquotes = 0
    headings = 0
    images = 0

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
        if IMAGE_LINE_RE.match(line):
            images += 1
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
            quotes = 0
            is_table = False
            while i < len(lines) and lines[i].strip():
                if re.search(r'<table\b', lines[i], re.IGNORECASE):
                    is_table = True
                if re.search(r'<tr\b', lines[i], re.IGNORECASE):
                    rows += 1
                quotes += len(re.findall(r'<blockquote\b', lines[i], re.IGNORECASE))
                i += 1
            if is_table:
                tables.append({"rows": rows})
            elif quotes:
                blockquotes += quotes
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
        "images": images,
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


def read_urls(urls_path):
    """Parse what qingyun-file-hosting printed: a JSON array of URLs (null
    for a failed file), or a bare URL when it was given a single file."""
    with open(urls_path, encoding="utf-8") as fh:
        raw = fh.read().strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [raw or None]


# Hosts whose links a platform cannot show. An output with any gets its own
# upload with those hosts excluded; the other outputs share an upload over the
# full host queue.
EXCLUDED_HOSTS = {"weixin": ["sxcu", "uguu"]}


def swap_placeholders(outputs, urls, texts, warnings):
    """Point each hosted image's markdown at its URL, in the given outputs.

    The URLs are for the images still holding a placeholder in those outputs,
    in manifest order. An image with no URL keeps its placeholder, so it can
    be inserted by hand after import.
    """
    pending = [e for e in outputs[0]["images"] if e["placeholder"]]
    for entry, url in zip(pending, urls):
        if not url:
            warnings.append(
                "image %d was not hosted for %s, so it keeps placeholder %s "
                "for manual insertion" % (
                    entry["index"], ", ".join(o["variant"] for o in outputs),
                    entry["placeholder"]))
            continue
        for output in outputs:
            mine = next(e for e in output["images"] if e["index"] == entry["index"])
            texts[output["variant"]] = texts[output["variant"]].replace(
                mine["placeholder"], "![](%s)" % url)
            mine["hosted_url"] = url
            mine["placeholder"] = None
    return texts


# --- Platform variants ------------------------------------------------------
#
# Every output gets the processing any markdown import needs: blank lines
# between blocks, the title lifted out, images downloaded and hosted. On top
# of that, a variant carries only what its platform's editor needs. RedNote has
# no processing of its own yet, so it shares the unspecified output.

VARIANTS_BY_PLATFORM = {
    "unspecified": ["unspecified"],
    "weixin": ["weixin"],
    "rednote": ["unspecified"],
    "zhihu": ["zhihu"],
    "all": ["unspecified", "zhihu", "weixin"],
}

# A numbered list item at the top level -- not inside a quote, not nested.
TOP_NUMBERED_RE = re.compile(r'^\d{1,9}[.)][ \t]+\S')
QUOTE_PREFIX_RE = re.compile(r'^\s*>[ ]?')


def _quote_runs(lines):
    """Yield (start, end) for each run of quote lines outside code fences."""
    in_fence = False
    i = 0
    while i < len(lines):
        if FENCE_LINE_RE.match(lines[i]):
            in_fence = not in_fence
        if in_fence or not QUOTE_LINE_RE.match(lines[i]):
            i += 1
            continue
        start = i
        while i < len(lines) and QUOTE_LINE_RE.match(lines[i]):
            i += 1
        yield start, i


def rewrite_quotes_for_zhihu(text):
    """Rewrite two quote shapes as HTML, for Zhihu.

    - A quote holding only a numbered list becomes a `>` line followed by one
      `<li>...</li>` line per item.
    - Two or more one-line quotes in a row, with only blank lines between
      them, become consecutive `<blockquote>...</blockquote>` lines. A
      one-line quote standing alone is left as it is.
    """
    lines = text.split("\n")
    # Classify each quote block: ("list", items), ("line", text) or None.
    blocks = []
    for start, end in _quote_runs(lines):
        contents = [QUOTE_PREFIX_RE.sub("", l, count=1).rstrip() for l in lines[start:end]]
        filled = [c for c in contents if c.strip()]
        if filled and all(TOP_NUMBERED_RE.match(c) for c in filled):
            blocks.append((start, end, "list", filled))
        elif (len(filled) == 1 and contents[0].strip()
                and not QUOTE_LINE_RE.match(filled[0])):
            blocks.append((start, end, "line", filled[0]))

    replace = {}  # start -> (end, new lines)
    for start, end, kind, value in blocks:
        if kind == "list":
            replace[start] = (end, [">"] + ["<li>%s</li>" % c for c in value])

    # Group one-line quotes separated only by blank lines.
    group = []

    def flush():
        if len(group) > 1:
            first, last = group[0][0], group[-1][1]
            replace[first] = (last, ["<blockquote>%s</blockquote>" % g[2]
                                     for g in group])
        group.clear()

    for start, end, kind, value in blocks:
        if kind != "line":
            flush()
            continue
        if group and any(l.strip() for l in lines[group[-1][1]:start]):
            flush()
        group.append((start, end, value))
    flush()

    out = []
    i = 0
    while i < len(lines):
        if i in replace:
            end, new = replace[i]
            out.extend(new)
            i = end
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def wrap_numbered_items(text):
    """Wrap each top-level numbered list item in <li></li>, for Weixin.

    Returns (text, warnings). Items inside quotes, nested items and bulleted
    items are left alone. An item followed by indented lines (nested content
    or a continuation) is wrapped on its own line only, and reported, since
    those lines are no longer inside a markdown list once the item is HTML.
    """
    lines = text.split("\n")
    warnings = []
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_LINE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not TOP_NUMBERED_RE.match(line):
            continue
        lines[i] = "<li>%s</li>" % line.rstrip()
        following = lines[i + 1] if i + 1 < len(lines) else ""
        if following[:1] in (" ", "\t") and following.strip():
            warnings.append(
                "numbered item %r has indented lines under it, which are "
                "left outside its <li>" % line.strip()[:40])
    return "\n".join(lines), warnings


def variant_body(text, variant, title_override):
    """Run one variant's text processing on the raw source.

    Returns (title, body, blank_lines_inserted, soft_wrapped_lines, warnings).
    """
    if variant == "zhihu":
        text = convert_html_tables(text)
    text, blanks_inserted, soft_wraps = normalize_source(text)

    if title_override:
        title = title_override
    else:
        title, text = extract_title(text)
        if title is None:
            raise SystemExit(
                "No title: the source has no '# ' heading and --title was "
                "not given. Platforms never fill the title in from the body, "
                "so the article would go out untitled. Pass --title "
                "explicitly (for a Notion source, its properties.title).")
    if not title.strip():
        raise SystemExit("The title is empty; refusing to process an "
                         "untitled article.")

    warnings = []
    if variant == "zhihu":
        text, warnings = flatten_lists(text)
        text = rewrite_quotes_for_zhihu(text)
    elif variant == "weixin":
        text, warnings = wrap_numbered_items(text)

    # Paragraph lines left joined because the line above them broke
    # mid-sentence. Usually right, but it is also what a genuinely merged
    # source looks like, so say so rather than deciding silently.
    if soft_wraps:
        warnings.append(
            "%d paragraph or quote line(s) were treated as soft wrapping and "
            "left joined to the line above, because that line did not end on "
            "sentence-final punctuation. If the article reads as merged "
            "paragraphs or blockquotes, the source lost its blank lines "
            "before reaching this script." % soft_wraps)
    return title, text, blanks_inserted, soft_wraps, warnings


def finish(manifest, texts):
    """Write every output file and manifest.json for the current texts."""
    for output in manifest["outputs"]:
        text = texts[output["variant"]]
        structure = describe_structure(text)
        structure["placeholders"] = sum(
            1 for entry in output["images"]
            if entry["placeholder"] and entry["placeholder"] in text)
        output["expected_structure"] = structure
        with open(output["processed_markdown"], "w", encoding="utf-8") as fh:
            fh.write(text)

    # The top-level images describe the outputs on the full host queue (or,
    # when every output excludes some hosts, the first output).
    reference = next((o for o in manifest["outputs"] if not o["excluded_hosts"]),
                     manifest["outputs"][0])
    for image, entry in zip(manifest["images"], reference["images"]):
        image["hosted_url"] = entry["hosted_url"]
        image["placeholder"] = entry["placeholder"]

    with open(manifest["manifest"], "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


def prepare(source_path, out_dir, platform, title_override=None):
    source_path = os.path.abspath(source_path)
    source_dir = os.path.dirname(source_path)

    with open(source_path, encoding="utf-8") as fh:
        source_text = fh.read()

    os.makedirs(out_dir, exist_ok=True)
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Each image is downloaded once and shared by every variant: the k-th
    # reference to a URL in any variant is the same image as the k-th
    # reference to it in another.
    images = []
    errors = []
    by_url = {}  # url -> [image record or None (download failed), ...]
    seen = [0]  # images encountered, including ones that failed to download

    def fetch_once(url, occurrence):
        records = by_url.setdefault(url, [])
        if occurrence < len(records):
            return records[occurrence]
        seen[0] += 1
        idx = seen[0]
        dest_no_ext = os.path.join(images_dir, "img-%d" % idx)
        try:
            local_path = fetch_image(url, dest_no_ext, source_dir)
        except Exception as exc:  # noqa: BLE001 - report, don't abort the run
            errors.append({"index": idx, "source_url": url, "error": str(exc)})
            records.append(None)
            return None
        image = {
            "index": idx,
            "placeholder": PLACEHOLDER_TMPL.format(n=idx),
            "source_url": url,
            "local_path": os.path.abspath(local_path),
            "hosted_url": None,
        }
        images.append(image)
        records.append(image)
        return image

    title = None
    texts = {}
    outputs = []
    for variant in VARIANTS_BY_PLATFORM[platform]:
        title, body, blanks_inserted, soft_wraps, warnings = variant_body(
            source_text, variant, title_override)
        occurrences = {}

        def replace(match):
            url = match.group("md_url") or match.group("html_url")
            occurrence = occurrences.get(url, 0)
            occurrences[url] = occurrence + 1
            image = fetch_once(url, occurrence)
            if image is None:
                return match.group(0)  # leave the original markdown untouched
            # Isolate the placeholder on its own paragraph.
            return "\n\n%s\n\n" % image["placeholder"]

        texts[variant] = IMAGE_RE.sub(replace, body)
        outputs.append({
            "variant": variant,
            "processed_markdown": os.path.abspath(
                os.path.join(out_dir, variant + ".md")),
            "blank_lines_inserted": blanks_inserted,
            "soft_wrapped_lines": soft_wraps,
            "expected_structure": None,
            "warnings": warnings,
            "excluded_hosts": EXCLUDED_HOSTS.get(variant, []),
        })

    # Each output records its own image links, since an output with excluded
    # hosts is uploaded separately and can link an image elsewhere.
    for output in outputs:
        output["images"] = [{"index": image["index"],
                             "placeholder": image["placeholder"],
                             "hosted_url": None} for image in images]

    manifest = {
        "title": title,
        "source": source_path,
        "platform": platform,
        "manifest": os.path.abspath(os.path.join(out_dir, "manifest.json")),
        "images_dir": os.path.abspath(images_dir),
        "images": images,
        "outputs": outputs,
        "warnings": [],
        "errors": errors,
    }
    return finish(manifest, texts)


def finalize(manifest_path, urls_path, variants=None):
    """Swap in one upload's URLs for the chosen outputs.

    `variants` names the outputs the upload was for; by default, every output
    with no excluded hosts -- the ones sharing the full-queue upload.
    """
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    texts = {}
    for output in manifest["outputs"]:
        with open(output["processed_markdown"], encoding="utf-8") as fh:
            texts[output["variant"]] = fh.read()

    if variants:
        outputs = [o for o in manifest["outputs"] if o["variant"] in variants]
        missing = set(variants) - {o["variant"] for o in outputs}
        if missing:
            raise SystemExit("no output named %s in this manifest"
                             % ", ".join(sorted(missing)))
    else:
        outputs = [o for o in manifest["outputs"] if not o["excluded_hosts"]]
        if not outputs:
            raise SystemExit("every output in this manifest excludes some "
                             "hosts; name the upload's outputs with --variants")
    pending = [[e["index"] for e in o["images"] if e["placeholder"]] for o in outputs]
    if any(p != pending[0] for p in pending[1:]):
        raise SystemExit("%s have different images left to host; finalize "
                         "them separately" % ", ".join(o["variant"] for o in outputs))

    urls = read_urls(urls_path)
    if len(urls) != len(pending[0]):
        raise SystemExit(
            "got %d URL(s) for %d image(s) still holding a placeholder in %s; "
            "the upload must cover exactly those images, in manifest order"
            % (len(urls), len(pending[0]), ", ".join(o["variant"] for o in outputs)))

    texts = swap_placeholders(outputs, urls, texts, manifest["warnings"])
    return finish(manifest, texts)


def main():
    ap = argparse.ArgumentParser(
        description="qingyun-process-md: prepare a local markdown article "
                     "(title + placeholder'd images), then swap in the "
                     "images' hosted URLs")
    stages = ap.add_subparsers(dest="stage", required=True)

    prep = stages.add_parser(
        "prepare", help="normalize the markdown, download every image and "
                        "replace it with a placeholder")
    prep.add_argument("--source", required=True,
                      help="path to the local markdown file")
    prep.add_argument("--title", default=None,
                      help="override title instead of auto-detecting the "
                           "first heading")
    prep.add_argument("--platform", default="all",
                      type=str.lower, choices=sorted(VARIANTS_BY_PLATFORM),
                      help="which platform's output(s) to write (default: "
                           "all); unspecified and rednote share the "
                           "unspecified output")
    prep.add_argument("--out-dir", default=None,
                      help="where to write the output .md file(s), "
                           "manifest.json and images/ (default: a sibling "
                           "'<name>-processed' folder next to the source file)")

    notion = stages.add_parser(
        "notion", help="convert a notion-fetch <content> block into the "
                       "markdown the Notion app's export writes")
    notion.add_argument("--input", required=True,
                        help="file holding the <content> block verbatim")
    notion.add_argument("--title", required=True,
                        help="the page title, written as the '# ' heading")
    notion.add_argument("--output", required=True,
                        help="where to write the converted markdown")

    fin = stages.add_parser(
        "finalize", help="swap each placeholder for its hosted image URL")
    fin.add_argument("--manifest", required=True,
                     help="the manifest.json that prepare wrote")
    fin.add_argument("--urls-file", required=True,
                     help="file holding qingyun-file-hosting's stdout for "
                          "the outputs' images still holding a placeholder")
    fin.add_argument("--variants", default=None,
                     type=lambda s: [v.strip().lower() for v in s.split(",") if v.strip()],
                     help="comma-separated outputs the upload was for "
                          "(default: every output with no excluded hosts)")
    args = ap.parse_args()

    if args.stage == "notion":
        with open(args.input, encoding="utf-8") as fh:
            markdown, warnings = notion_md.convert(fh.read(), args.title)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        print(json.dumps({"output": os.path.abspath(args.output),
                          "warnings": warnings}, ensure_ascii=False, indent=2))
        return

    if args.stage == "prepare":
        if not os.path.isfile(args.source):
            raise SystemExit("source markdown not found: %s" % args.source)
        out_dir = args.out_dir
        if not out_dir:
            base = os.path.splitext(os.path.basename(args.source))[0]
            out_dir = os.path.join(os.path.dirname(os.path.abspath(args.source)),
                                    base + "-processed")
        manifest = prepare(args.source, out_dir, args.platform, args.title)
    else:
        manifest = finalize(args.manifest, args.urls_file, args.variants)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if manifest["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
