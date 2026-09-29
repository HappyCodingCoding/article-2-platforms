"""Converts Notion-flavored ("enhanced") markdown, as `notion-fetch` returns
it, into standard markdown laid out the way the Notion app's own
Export -> Markdown writes it.

Called by script.py only. Format reference: `notion://docs/enhanced-markdown-spec`
(read it with `notion-fetch`).

The two formats carry the same content; they differ in how it is written:

- Nesting. Notion-flavored markdown puts a block's children on the lines
  below it, indented one tab deeper. The export writes a quote's children
  with a `> ` prefix and a list item's children indented four spaces.
- Escapes. Notion-flavored markdown backslash-escapes \\ * ~ ` $ [ ] < > { } | ^
  in rich text; the export writes them bare.
- Block separation. Notion-flavored markdown puts one block per line; the
  export separates blocks with a blank line, except consecutive items of one
  list, and closes every quote with a `> ` line.
- Notion-only syntax: `<empty-block/>`, `{color="..."}` attribute lists,
  `<span>` colours and underline, mentions, callouts, toggles, columns and
  HTML tables, each rewritten as the export writes it.

Only paragraphs, bold, inline code, numbered lists, quotes (with and without
children), images and `<empty-block/>` have been checked byte for byte
against a real export; the other block types follow the export's known
conventions and are listed as unverified in the returned warnings whenever
an article contains one.
"""

import os
import re
from urllib.parse import unquote, urlparse

ESCAPE_RE = re.compile(r'\\([\\*~`$\[\]<>{}|^])')
ATTRS_RE = re.compile(r'\s*\{(?:[a-z-]+="[^"]*"\s*)+\}\s*$')
SPAN_RE = re.compile(r'<span\b[^>]*>(.*?)</span>', re.DOTALL)
MENTION_LINK_RE = re.compile(
    r'<mention-(?:page|database|data-source|agent)\b[^>]*?url="([^"]*)"[^>]*?'
    r'(?:/>|>(.*?)</mention-(?:page|database|data-source|agent)>)', re.DOTALL)
MENTION_USER_RE = re.compile(
    r'<mention-user\b[^>]*?(?:/>|>(.*?)</mention-user>)', re.DOTALL)
MENTION_DATE_RE = re.compile(
    r'<mention-date\b[^>]*?start="([^"]*)"(?:[^>]*?end="([^"]*)")?[^>]*/>')
INLINE_MATH_RE = re.compile(r'\$`([^`]*)`\$')
BR_RE = re.compile(r'<br\s*/?>')

IMAGE_LINE_RE = re.compile(r'^!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)\)$')
LIST_RE = re.compile(r'^(?P<marker>[-*+]|\d{1,9}[.)])(?: (?P<todo>\[[ xX]\]))?(?: (?P<text>.*))?$')
HEADING_RE = re.compile(r'^(#{1,6}) (.*)$')
FENCE_RE = re.compile(r'^(```|~~~)(.*)$')
OPEN_TAG_RE = re.compile(r'^<([a-z_-]+)\b([^>]*?)(/?)>(.*)$')
ATTR_RE = re.compile(r'([a-z-]+)="([^"]*)"')

# Block types whose rendering has not been checked against a real export.
UNVERIFIED = {"heading", "bulleted", "todo", "code", "equation", "divider",
              "table", "callout", "toggle", "link-block", "unknown",
              "text-children", "multi-line quote"}

VERIFIED_TAGS = {"empty-block"}
LINK_TAGS = {"page", "database", "folder", "file", "pdf", "video", "audio",
             "embed"}


def _depth(line):
    return len(line) - len(line.lstrip("\t"))


def inline(text):
    """Convert one run of Notion-flavored rich text to export markdown."""
    text = ATTRS_RE.sub("", text)
    # Code spans are literal: unescape only between them.
    parts = re.split(r'(`[^`]*`)', text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(part)
            continue
        part = MENTION_LINK_RE.sub(lambda m: "[%s](%s)" % (m.group(2) or m.group(1), m.group(1)), part)
        part = MENTION_USER_RE.sub(lambda m: "@" + (m.group(1) or "user"), part)
        part = MENTION_DATE_RE.sub(lambda m: m.group(1) + (" → " + m.group(2) if m.group(2) else ""), part)
        while SPAN_RE.search(part):
            part = SPAN_RE.sub(r'\1', part)
        part = ESCAPE_RE.sub(r'\1', part)
        out.append(part)
    return INLINE_MATH_RE.sub(r'$\1$', "".join(out))


class Block:
    def __init__(self, kind, text="", children=None, **extra):
        self.kind = kind
        self.text = text
        self.children = children or []
        self.extra = extra


def _collect_until(lines, i, closing, depth):
    """Lines from i up to (not including) the line `closing` at `depth`."""
    body = []
    while i < len(lines):
        line = lines[i]
        if line.strip() == closing and _depth(line) <= depth:
            return body, i + 1
        body.append(line)
        i += 1
    return body, i


def _dedent(lines, depth):
    return [l[depth:] if l[:depth] == "\t" * depth else l.lstrip("\t") for l in lines]


def parse(lines, depth=0):
    """Parse lines at `depth` (tabs) into a list of Blocks."""
    blocks = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            i += 1  # plain empty lines carry no content in this format
            continue
        d = _depth(raw)
        line = raw[d:]
        i += 1

        fence = FENCE_RE.match(line)
        if fence:
            body, i = _collect_until(lines, i, fence.group(1), d)
            blocks.append(Block("code", "\n".join(_dedent(body, d)),
                                lang=fence.group(2).strip()))
            continue
        if line.strip() == "$$":
            body, i = _collect_until(lines, i, "$$", d)
            blocks.append(Block("equation", "\n".join(_dedent(body, d))))
            continue

        tag = OPEN_TAG_RE.match(line)
        if tag:
            name, attrs, selfclose, rest = tag.groups()
            attrs = dict(ATTR_RE.findall(attrs))
            if name == "empty-block":
                blocks.append(Block("empty"))
                continue
            if name == "table":
                body, i = _collect_until(lines, i, "</table>", d)
                blocks.append(Block("table", "\n".join(body), **attrs))
                continue
            if name in ("callout", "details", "columns", "column", "tabs",
                        "tab", "synced_block", "synced_block_reference"):
                if selfclose:
                    continue
                body, i = _collect_until(lines, i, "</%s>" % name, d)
                if name == "details":
                    summary = ""
                    if body and "<summary>" in body[0]:
                        summary = re.sub(r'</?summary>', "", body[0].strip())
                        body = body[1:]
                    inner = parse(_dedent(body, d + 1) if all(
                        _depth(l) > d or not l.strip() for l in body) else _dedent(body, d))
                    blocks.append(Block("toggle", summary, inner))
                elif name == "callout":
                    blocks.append(Block("callout", "", parse(_dedent(body, d + 1)),
                                        icon=attrs.get("icon", "")))
                else:  # containers with no markup of their own
                    blocks.extend(parse(_dedent(body, d + 1)))
                continue
            if name in LINK_TAGS:
                m = re.match(r'(.*?)</%s>' % name, rest)
                title = m.group(1) if m else ""
                url = attrs.get("url") or attrs.get("src", "")
                blocks.append(Block("link-block", title or url, url=url))
                continue
            if name == "table_of_contents":
                continue
            if not name.startswith("mention-") and name != "span":
                blocks.append(Block("unknown", line))
                continue

        # Children: every following line indented deeper than this block.
        child_lines = []
        while i < len(lines) and (not lines[i].strip() or _depth(lines[i]) > d):
            child_lines.append(lines[i])
            i += 1
        while child_lines and not child_lines[-1].strip():
            child_lines.pop()
            i -= 1
        children = parse(_dedent(child_lines, d + 1)) if child_lines else []

        if line.startswith(">") and (len(line) == 1 or line[1] == " "):
            blocks.append(Block("quote", line[2:], children))
            continue
        heading = HEADING_RE.match(line)
        if heading:
            blocks.append(Block("heading", heading.group(2), children,
                                level=len(heading.group(1))))
            continue
        if line.strip() == "---":
            blocks.append(Block("divider"))
            continue
        image = IMAGE_LINE_RE.match(ATTRS_RE.sub("", line))
        if image:
            blocks.append(Block("image", image.group("alt"), children,
                                url=image.group("url")))
            continue
        item = LIST_RE.match(line)
        if item:
            marker = item.group("marker")
            if item.group("todo"):
                kind = "todo"
            elif marker[0].isdigit():
                kind = "numbered"
            else:
                kind = "bulleted"
            blocks.append(Block(kind, item.group("text") or "", children,
                                marker=marker, todo=item.group("todo")))
            continue
        blocks.append(Block("text", line, children))
    return blocks


def _table(body):
    rows = []
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', body, re.DOTALL):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.DOTALL)
        rows.append([inline(c.strip()).replace("|", "\\|") for c in cells])
    if not rows:
        return [body]
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "| " + " | ".join(["---"] * width) + " |"]
    return out + ["| " + " | ".join(r) + " |" for r in rows[1:]]


def _indent(lines, prefix):
    return [prefix + l if l else "" for l in lines]


def render(blocks, used):
    """Render Blocks as export-style lines; `used` collects block kinds."""
    out = []
    prev = None
    for block in blocks:
        if block.kind == "empty":
            used.add("empty")
            continue
        lines = render_block(block, used)
        same_list = (prev is not None and prev.kind == block.kind
                     and block.kind in ("bulleted", "numbered", "todo"))
        if out and not same_list:
            out.append("")
        out.extend(lines)
        prev = block
    return out


def render_block(block, used):
    kind = block.kind
    used.add(kind)
    text = inline(block.text)
    children = render(block.children, used) if block.children else []

    if kind == "quote":
        rows = BR_RE.split(text)
        if len(rows) > 1:
            used.add("multi-line quote")
        lines = ["> " + r for r in rows] + ["> "]
        return lines + ["> " + l if l else "> " for l in children]
    if kind in ("bulleted", "numbered", "todo"):
        head = block.extra["marker"]
        if block.extra.get("todo"):
            head += " " + block.extra["todo"]
        lines = [(head + " " + text).rstrip()]
        return lines + _indent(children, "    ")
    if kind == "heading":
        return ["#" * block.extra["level"] + " " + text] + (
            [""] + children if children else [])
    if kind == "image":
        alt = text or unquote(os.path.basename(urlparse(block.extra["url"]).path))
        return ["![%s](%s)" % (alt, block.extra["url"])] + (
            [""] + children if children else [])
    if kind == "divider":
        return ["---"]
    if kind == "code":
        return ["```" + block.extra.get("lang", "")] + block.text.split("\n") + ["```"]
    if kind == "equation":
        return ["$$", block.text, "$$"]
    if kind == "table":
        return _table(block.text)
    if kind == "callout":
        body = children or [""]
        icon = block.extra.get("icon", "")
        first = (icon + " " + body[0]).strip() if icon else body[0]
        return ["<aside>", first] + body[1:] + ["", "</aside>"]
    if kind == "toggle":
        return ["- " + text] + _indent(children, "    ")
    if kind == "link-block":
        return ["[%s](%s)" % (text, block.extra["url"])]
    if kind == "unknown":
        return [block.text]
    # text
    lines = BR_RE.split(text)
    if children:
        used.add("text-children")
        lines += _indent(children, "    ")
    return lines


def convert(content, title):
    """Return (markdown, warnings) for a notion-fetch <content> block."""
    used = set()
    blocks = parse(content.strip("\n").split("\n"))
    body = render(blocks, used)
    # The page title becomes the first line, as in the export, unless the
    # body already opens with a title of its own (a level-1 heading).
    first = next((b for b in blocks if b.kind != "empty"), None)
    has_title = (first is not None and first.kind == "heading"
                 and first.extra.get("level") == 1)
    lines = ["# " + title, ""] + body if title and not has_title else body
    warnings = []
    # Only a bare `~` has been seen in a real export. Any other character
    # Notion escaped is written bare the same way, where it can start
    # emphasis, a link or HTML that the page did not have.
    unescaped = sorted(set(ESCAPE_RE.findall(re.sub(r'`[^`\n]*`', "", content))) - {"~"})
    if unescaped:
        warnings.append(
            "the page escapes %s in its text; they are written bare, as the "
            "Notion export writes `~`, which has not been checked for these "
            "characters. Check that no text around them turned into "
            "emphasis, a link or HTML." % " ".join(unescaped))
    unverified = sorted(used & UNVERIFIED)
    if unverified:
        warnings.append(
            "the page contains block types whose conversion has not been "
            "checked against a real Notion export: %s. Compare those parts "
            "with the page in Notion." % ", ".join(unverified))
    return "\n".join(lines), warnings
