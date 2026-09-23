"""The hosting providers this skill can upload to, and what each one accepts.

Called by script.py only. To add a provider, subclass Provider, fill in its
limits, implement upload(), and add it to PROVIDERS at its place in the
fallback queue.
"""

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
    banned_extensions = ()

    def refusal(self, path, size):
        """Why this provider cannot take the file, or None if it can."""
        ext = os.path.splitext(path)[1].lower()
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


# In fallback-queue order.
PROVIDERS = [Litterbox(), Catbox()]
PROVIDERS_BY_NAME = {p.name: p for p in PROVIDERS}


def _require_url(provider_name, reply):
    parsed = urlparse(reply)
    if parsed.scheme in ("http", "https") and parsed.netloc and " " not in reply:
        return reply
    raise RejectedError("%s replied: %s" % (provider_name, reply[:300] or "(empty)"))
