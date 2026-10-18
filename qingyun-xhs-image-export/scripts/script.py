#!/usr/bin/env python3
"""Main script for the qingyun-xhs-image-export skill: receives the card
images Xiaohongshu (小红书) renders for a 写长文 note's 一键排版 layout and
saves them to a local folder, in each aspect ratio asked for.

Usage:
    python3 script.py receive --output-dir <dir> [--prefix xhs-card] [--aspects 3:5,3:4] [--timeout 600]

Why a receiver is needed: after 下一步, the publish page holds every
rendered card as a `blob:` URL that only that page can read, and the page
cannot hand the bytes to this machine directly -- fetch/XHR to localhost,
<a download>, popups and cross-origin iframes are all blocked or go
nowhere. What does survive is `window.name`, which a tab keeps across a
top-level navigation. So the agent packs the images into `window.name` on
the XHS page, then navigates that same tab to this receiver's page, whose
own script reads `window.name` back and posts each image to this server,
same-origin.

`receive`:
    1. Binds a server on 127.0.0.1 to a free port and makes a random token.
    2. Prints one JSON line, {"receiver_url": ..., "token": ...}, and
       flushes it. The agent puts the token into the payload and navigates
       the XHS tab to receiver_url.
    3. Serves the receiver page at /<token>. That page reads window.name,
       clears it, checks the token, posts every image to
       /<token>/image/<n>, then posts {title, count} to /<token>/done.
    4. On done, writes each card once per aspect in --aspects:
       - 3:5, XHS's own ratio: the file exactly as received, saved as
         <output-dir>/<prefix>-<n>.<ext>, with the extension taken from
         the file's own bytes (XHS renders JPEG);
       - 3:4: the card padded at the sides to 3:4 by pad.py, nothing cut
         off, saved as <output-dir>/3x4/<prefix>-<n>.jpg.
       Then writes manifest.json to the output dir, prints it and exits 0.
    5. Exits 1 with an error JSON when the page reports a problem, or when
       nothing has arrived within --timeout seconds.

This script never touches Xiaohongshu itself and never publishes anything.
"""

import argparse
import http.server
import json
import os
import secrets
import struct
import sys
import threading

pad = None  # pad.py, imported by receive() only when an aspect needs padding

NATIVE_ASPECT = (3, 5)  # every 一键排版 card is 900x1500, exported at 1440x2400
SUPPORTED_ASPECTS = [NATIVE_ASPECT, (3, 4)]

RECEIVER_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>XHS-EXPORT-WAITING</title>
<body style="font:16px system-ui;padding:24px">
<p id="status">Receiving images…</p>
<script>
(async () => {
  const TOKEN = "__TOKEN__";
  const status = document.getElementById('status');
  const post = (path, body) => fetch('/' + TOKEN + path, { method: 'POST', body });
  const fail = async (message) => {
    document.title = 'XHS-EXPORT-ERROR';
    status.textContent = 'Error: ' + message;
    await post('/error', JSON.stringify({ error: message }));
  };
  const raw = window.name;
  window.name = '';
  let payload;
  try { payload = JSON.parse(raw); } catch (e) { return fail('window.name holds no export payload'); }
  if (!payload || payload.token !== TOKEN) return fail('payload token does not match this receiver');
  const images = payload.images || [];
  if (!images.length) return fail('payload holds no images');
  for (let i = 0; i < images.length; i++) {
    const blob = await (await fetch(images[i])).blob();
    const r = await post('/image/' + (i + 1), blob);
    if (!r.ok) return fail('image ' + (i + 1) + ' was refused: HTTP ' + r.status);
    status.textContent = 'Saved ' + (i + 1) + ' / ' + images.length;
  }
  await post('/done', JSON.stringify({ title: payload.title || '', count: images.length }));
  document.title = 'XHS-EXPORT-DONE ' + images.length;
  status.textContent = 'Done: ' + images.length + ' images saved. You can go back to Xiaohongshu.';
})();
</script>
"""


def sniff_format(data):
    """Return (extension, width, height) read from the image's own header."""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg", *jpeg_size(data)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return ".png", width, height
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", *webp_size(data)
    return ".bin", None, None


def jpeg_size(data):
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        # SOF0..SOF15, except DHT (C4), JPG (C8) and DAC (CC)
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    return None, None


def webp_size(data):
    chunk = data[12:16]
    if chunk == b"VP8 ":
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    return None, None


def parse_aspects(value):
    """'3:5,3:4' -> [(3, 5), (3, 4)], keeping order and dropping repeats."""
    aspects = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            aspect = tuple(int(x) for x in part.split(":"))
        except ValueError:
            aspect = None
        if aspect not in SUPPORTED_ASPECTS:
            supported = ", ".join(aspect_label(a) for a in SUPPORTED_ASPECTS)
            raise argparse.ArgumentTypeError(f"unsupported aspect {part!r}; use {supported}")
        if aspect not in aspects:
            aspects.append(aspect)
    if not aspects:
        raise argparse.ArgumentTypeError("no aspect given")
    return aspects


def aspect_label(aspect):
    return f"{aspect[0]}:{aspect[1]}"


def aspect_folder(aspect):
    return f"{aspect[0]}x{aspect[1]}"


def receive(args):
    aspects = args.aspects
    if any(a != NATIVE_ASPECT for a in aspects):
        # Fail before the export, not after the images have arrived.
        global pad
        try:
            import pad
        except ImportError:
            print(json.dumps({"error": "padding needs Pillow: pip install pillow"}), flush=True)
            return 1
    output_dir = os.path.abspath(os.path.expanduser(args.output_dir))
    os.makedirs(output_dir, exist_ok=True)
    token = secrets.token_hex(8)
    received = {}  # index -> bytes
    result = {}
    finished = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, body=b"", content_type="text/plain"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.split("?")[0] != "/" + token:
                return self.reply(404)
            page = RECEIVER_PAGE.replace("__TOKEN__", token).encode()
            self.reply(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            parts = self.path.strip("/").split("/")
            if not parts or parts[0] != token:
                return self.reply(404)
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            action = parts[1] if len(parts) > 1 else ""
            if action == "image" and len(parts) == 3 and parts[2].isdigit():
                received[int(parts[2])] = body
                return self.reply(200, b"ok")
            if action == "done":
                result.update(done=json.loads(body or b"{}"))
                self.reply(200, b"ok")
                finished.set()
                return
            if action == "error":
                result.update(error=json.loads(body or b"{}").get("error", "unknown"))
                self.reply(200, b"ok")
                finished.set()
                return
            self.reply(404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({"receiver_url": f"http://127.0.0.1:{port}/{token}", "token": token}), flush=True)

    arrived = finished.wait(args.timeout)
    server.shutdown()

    if not arrived:
        print(json.dumps({"error": f"no export arrived within {args.timeout} seconds"}), flush=True)
        return 1
    if "error" in result:
        print(json.dumps({"error": result["error"]}, ensure_ascii=False), flush=True)
        return 1

    expected = result["done"].get("count", len(received))
    missing = [n for n in range(1, expected + 1) if n not in received]
    images = []
    for aspect in aspects:
        folder = output_dir if aspect == NATIVE_ASPECT else os.path.join(output_dir, aspect_folder(aspect))
        os.makedirs(folder, exist_ok=True)
        for n in sorted(received):
            data = received[n]
            if aspect == NATIVE_ASPECT:
                ext, width, height = sniff_format(data)
            else:
                data, width, height = pad.pad_to_aspect(data, *aspect)
                ext = ".jpg"
            path = os.path.join(folder, f"{args.prefix}-{n}{ext}")
            with open(path, "wb") as f:
                f.write(data)
            images.append({"index": n, "aspect": aspect_label(aspect), "path": path,
                           "format": ext.lstrip("."), "width": width, "height": height,
                           "bytes": len(data)})

    manifest = {
        "title": result["done"].get("title", ""),
        "output_dir": output_dir,
        "aspects": [aspect_label(a) for a in aspects],
        "expected": expected,
        "saved": len(received),
        "missing": missing,
        "images": images,
    }
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if not missing else 1


def main():
    ap = argparse.ArgumentParser(description="Receive Xiaohongshu card images exported from the browser.")
    stages = ap.add_subparsers(dest="stage", required=True)
    rec = stages.add_parser("receive", help="Run the local receiver until one export arrives.")
    rec.add_argument("--output-dir", required=True, help="Folder the images and manifest.json are written to.")
    rec.add_argument("--prefix", default="xhs-card", help="File name prefix; files are <prefix>-<n>.<ext>.")
    rec.add_argument("--timeout", type=int, default=600, help="Seconds to wait for the export before giving up.")
    rec.add_argument("--aspects", type=parse_aspects, default=parse_aspects("3:5,3:4"),
                     help="Comma-separated aspect ratios to save: 3:5 (XHS's own), 3:4 (padded). Default: 3:5,3:4.")
    args = ap.parse_args()
    if args.stage == "receive":
        sys.exit(receive(args))


if __name__ == "__main__":
    main()
