"""The hosting providers this skill can upload to, and what each one accepts.

Called by script.py only. To add a provider, subclass Provider, fill in its
limits, implement upload(), and add it to PROVIDERS at its place in the
reliability ranking.
"""

import json
import os
from urllib.parse import urlparse

from http_post import TransportError, post_files  # noqa: F401 — re-exported to script.py

MB = 1024 * 1024

# Catbox and Litterbox refuse these extensions ("doc*" covers .doc, .docx,
# .docm and the like).
CATBOX_BANNED_EXTENSIONS = (".exe", ".scr", ".cpl", ".jar", ".doc")


class RejectedError(Exception):
    """The provider replied, but with a message instead of a URL."""


class Provider:
    name = ""
    persistence = ""          # "permanent" or "temporary"
    accepts = ""              # "any" (any file, images included) or "image"
    expiry = None             # how long a temporary upload lives, e.g. "24h"
    max_file_bytes = 0
    max_files_per_request = 1
    max_request_bytes = 0     # total size cap for one multi-file request
    allowed_extensions = ()   # when set, the only extensions it takes
    banned_extensions = ()
    # Types it takes but serves back as a different format, losing what the
    # original was (e.g. an SVG's vectors). Passed on like a refused type.
    converted_extensions = {}  # extension -> the format it is served as

    def unavailable(self):
        """Why this provider cannot be used at all on this machine, or None."""
        return None

    def refusal(self, path, size):
        """Why this provider cannot take the file, or None if it can."""
        ext = os.path.splitext(path)[1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            return "%s does not take %s files" % (self.name, ext)
        if any(ext.startswith(banned) for banned in self.banned_extensions):
            return "%s refuses %s files" % (self.name, ext)
        if ext in self.converted_extensions:
            return "%s would serve %s files as %s" % (
                self.name, ext, self.converted_extensions[ext])
        if size > self.max_file_bytes:
            return "%s allows at most %s per file" % (
                self.name, _megabytes(self.max_file_bytes))
        return None

    def upload(self, paths):
        """Upload `paths` in one request and return their URLs in order."""
        raise NotImplementedError


class Uguu(Provider):
    name = "uguu"
    persistence = "temporary"
    accepts = "any"
    expiry = "3h"                # fixed by the site; the API takes no expiry field
    max_file_bytes = 128 * MB
    max_request_bytes = 128 * MB
    # Confirmed by probing real uploads (not published in the API docs):
    # refused. .doc .php .js .cgi .pl .py .sh .bmp .cpl are all accepted.
    banned_extensions = (".exe", ".scr", ".jar", ".docx", ".html", ".bat",
                         ".com", ".msi", ".svg")
    api = "https://uguu.se/upload"

    def upload(self, paths):
        reply = post_files(self.api, {}, "files[]", paths)
        try:
            payload = json.loads(reply)
        except ValueError:
            payload = None
        files = payload.get("files") if isinstance(payload, dict) else None
        url = files[0].get("url") if isinstance(files, list) and files else None
        return [_require_url(self.name, url or reply)]


class Sxcu(Provider):
    name = "sxcu"
    persistence = "permanent"   # nothing expires unless self_destruct is sent
    accepts = "image"
    # Whether the stated 95 MB is decimal or MiB is unknown; the decimal
    # figure is the smaller of the two, so it never sends a file sxcu refuses.
    max_file_bytes = 95 * 1000 * 1000
    max_request_bytes = 95 * 1000 * 1000
    # Its docs also list .bmp, but a real .bmp upload was refused.
    allowed_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp",
                          ".tif", ".tiff", ".ico")
    api = "https://sxcu.net/api/files/create"
    # The API docs ask every client to name itself as "name/version (+url)".
    user_agent = ("qingyun-file-hosting/1.0 "
                  "(+https://github.com/HappyCodingCoding/article-2-platforms)")

    def upload(self, paths):
        # noembed makes the reply's url the file itself, not its viewer page.
        reply = post_files(self.api, {"noembed": ""}, "file", paths,
                           user_agent=self.user_agent)
        try:
            payload = json.loads(reply)
        except ValueError:
            payload = None
        url = payload.get("url") if isinstance(payload, dict) else None
        return [_require_url(self.name, url or reply)]


class Kappa(Provider):
    name = "kappa"
    # It states no retention and its terms allow removing content at any
    # time, so it is never offered as permanent.
    persistence = "temporary"
    accepts = "any"           # took every type tested, .exe .html .svg included
    max_file_bytes = 100 * MB
    max_request_bytes = 100 * MB
    api = "https://kappa.lol/api/upload"

    def upload(self, paths):
        # The reply is JSON; `link` has no extension, and the site ignores one
        # appended to it, so `ext` is added back for readers that go by it.
        reply = post_files(self.api, {}, "file", paths)
        try:
            payload = json.loads(reply)
        except ValueError:
            payload = None
        url = None
        if isinstance(payload, dict) and payload.get("link"):
            url = payload["link"] + (payload.get("ext") or "")
        return [_require_url(self.name, url or reply)]


class Litterbox(Provider):
    name = "litterbox"
    persistence = "temporary"
    accepts = "any"
    expiry = "24h"
    max_file_bytes = 1024 * MB
    max_request_bytes = 1024 * MB
    banned_extensions = CATBOX_BANNED_EXTENSIONS
    api = "https://litterbox.catbox.moe/resources/internals/api.php"

    def upload(self, paths):
        reply = post_files(self.api, {"reqtype": "fileupload", "time": self.expiry},
                           "fileToUpload", paths)
        return [_require_url(self.name, reply)]


class Catbox(Provider):
    name = "catbox"
    persistence = "permanent"
    accepts = "any"
    max_file_bytes = 200 * MB
    max_request_bytes = 200 * MB
    banned_extensions = CATBOX_BANNED_EXTENSIONS
    api = "https://catbox.moe/user/api.php"

    def upload(self, paths):
        reply = post_files(self.api, {"reqtype": "fileupload"},
                           "fileToUpload", paths)
        return [_require_url(self.name, reply)]


class Picrd(Provider):
    name = "picrd"
    persistence = "permanent"   # nothing expires unless ttl_seconds is sent
    accepts = "image"
    max_file_bytes = 10 * MB
    max_request_bytes = 10 * MB
    # Other images (.svg, .bmp, ...) are refused with HTTP 400, so they are
    # passed on before being sent instead.
    allowed_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    api = "https://picrd.com/api/upload"

    def upload(self, paths):
        # The reply is JSON; the direct link is its image_url. Uploads are
        # unlisted by default, which keeps them off the site's public feed.
        reply = post_files(self.api, {}, "file", paths)
        try:
            payload = json.loads(reply)
        except ValueError:
            payload = None
        url = payload.get("image_url") if isinstance(payload, dict) else None
        return [_require_url(self.name, url or reply)]


class ImgBB(Provider):
    name = "imgbb"
    persistence = "permanent"   # nothing expires unless `expiration` is sent
    accepts = "image"           # every type script.py counts as an image
    converted_extensions = {
        ".svg": "JPEG", ".tif": "JPEG", ".tiff": "JPEG", ".bmp": "JPEG",
        ".heic": "AVIF", ".heif": "AVIF",
    }
    max_file_bytes = 32 * 1000 * 1000
    max_request_bytes = 32 * 1000 * 1000
    api = "https://api.imgbb.com/1/upload"
    # A personal key from the user's own ImgBB account. The environment
    # variable wins over the file.
    key_env = "IMGBB_API_KEY"
    key_file = os.path.expanduser("~/.config/qingyun-file-hosting/imgbb.key")

    def key(self):
        key = os.environ.get(self.key_env, "").strip()
        if not key and os.path.isfile(self.key_file):
            with open(self.key_file, encoding="utf-8") as fh:
                key = fh.read().strip()
        return key or None

    def unavailable(self):
        if self.key():
            return None
        return "imgbb needs an API key: set %s or save it to %s" % (
            self.key_env, self.key_file)

    def upload(self, paths):
        # The reply is JSON; the direct link is its data.url.
        reply = post_files(self.api, {"key": self.key()}, "image", paths)
        try:
            payload = json.loads(reply)
        except ValueError:
            payload = None
        data = payload.get("data") if isinstance(payload, dict) else None
        url = data.get("url") if isinstance(data, dict) else None
        return [_require_url(self.name, url or reply)]


class ImgCDN(Provider):
    name = "imgcdn"
    # The site calls its uploads permanent, but that applies to accounts; a
    # guest upload through the API comes back with an expiration date 14 days
    # out.
    persistence = "temporary"
    accepts = "image"
    expiry = "14d"
    max_file_bytes = 20 * MB
    max_request_bytes = 20 * MB
    # Images outside this list (.svg, .tiff, .heic, ...) are refused with a
    # non-URL reply, so they are passed on before being sent instead.
    allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    converted_extensions = {".bmp": "PNG"}
    api = "https://imgcdn.dev/api/1/upload"
    # The public guest key the site publishes at https://imgcdn.dev/page/api
    # for anonymous uploads; it belongs to no account.
    guest_key = "5386e05a3562c7a8f984e73401540836"

    def upload(self, paths):
        reply = post_files(self.api, {"key": self.guest_key, "format": "txt"},
                           "source", paths)
        return [_require_url(self.name, reply)]


# Ranked by observed reliability, most reliable first: hosts with no failed
# uploads in testing ahead of those with some, ties broken by speed and by
# how steady the service looks (imgcdn relies on a guest key that can be
# rotated). catbox had a timeout and 502s during one outage, picrd slow
# replies up to 21 s and a timeout, litterbox a 12h+ firewall block. sxcu is
# last by choice, as an extra fallback. Every fallback queue is this list
# filtered by the options, so each group keeps this order.
PROVIDERS = [Uguu(), Kappa(), ImgBB(), ImgCDN(), Catbox(), Picrd(), Litterbox(), Sxcu()]
PROVIDERS_BY_NAME = {p.name: p for p in PROVIDERS}


def _megabytes(n):
    """A size cap as the host states it: in MiB or in decimal megabytes."""
    return "%d MB" % (n // MB if n % MB == 0 else n // (1000 * 1000))


def _require_url(provider_name, reply):
    parsed = urlparse(reply)
    if parsed.scheme in ("http", "https") and parsed.netloc and " " not in reply:
        return reply
    raise RejectedError("%s replied: %s" % (provider_name, reply[:300] or "(empty)"))
