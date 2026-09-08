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
    5. Writes the processed markdown to <out-dir>/processed.md and prints a
       JSON manifest to stdout describing the title, the processed file, and
       every image (its placeholder text and local path, in upload order).

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


def process(source_path, out_dir, title_override=None):
    source_path = os.path.abspath(source_path)
    source_dir = os.path.dirname(source_path)

    with open(source_path, encoding="utf-8") as fh:
        text = fh.read()

    if title_override:
        title = title_override
    else:
        title, text = extract_title(text)
        if title is None:
            raise SystemExit(
                "No heading (# ...) found to use as the title. "
                "Pass --title explicitly instead.")

    os.makedirs(out_dir, exist_ok=True)
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    images = []
    errors = []

    def replace(match):
        idx = len(images) + 1
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

    processed_text = IMAGE_RE.sub(replace, text)

    processed_path = os.path.join(out_dir, "processed.md")
    with open(processed_path, "w", encoding="utf-8") as fh:
        fh.write(processed_text)

    return {
        "title": title,
        "source": source_path,
        "processed_markdown": os.path.abspath(processed_path),
        "images_dir": os.path.abspath(images_dir),
        "images": images,
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
