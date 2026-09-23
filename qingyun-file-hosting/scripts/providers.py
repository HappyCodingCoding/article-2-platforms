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

    def refusal(self, path, size):
        """Why this provider cannot take the file, or None if it can."""
        ext = os.path.splitext(path)[1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            return "%s does not take %s files" % (self.name, ext)
        if any(ext.startswith(banned) for banned in self.banned_extensions):
            return "%s refuses %s files" % (self.name, ext)
        if size > self.max_file_bytes:
            return "%s allows at most %d MB per file" % (
                self.name, self.max_file_bytes // MB)
        return None

    def upload(self, paths):
        """Upload `paths` in one request and return their URLs in order."""
        raise NotImplementedError


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
    api = "https://imgcdn.dev/api/1/upload"
    # The public guest key the site publishes at https://imgcdn.dev/page/api
    # for anonymous uploads; it belongs to no account.
    guest_key = "5386e05a3562c7a8f984e73401540836"

    def upload(self, paths):
        reply = post_files(self.api, {"key": self.guest_key, "format": "txt"},
                           "source", paths)
        return [_require_url(self.name, reply)]


# Ranked by stability and reliability, most reliable first. Every fallback
# queue is this list filtered by the options, so each group keeps this order.
PROVIDERS = [Catbox(), Picrd(), ImgCDN(), Litterbox()]
PROVIDERS_BY_NAME = {p.name: p for p in PROVIDERS}


def _require_url(provider_name, reply):
    parsed = urlparse(reply)
    if parsed.scheme in ("http", "https") and parsed.netloc and " " not in reply:
        return reply
    raise RejectedError("%s replied: %s" % (provider_name, reply[:300] or "(empty)"))
