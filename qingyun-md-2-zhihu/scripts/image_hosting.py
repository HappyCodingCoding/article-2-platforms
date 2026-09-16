"""Uploads local image files to the public image host img.scdn.io.

Called by script.py only. API reference: https://img.scdn.io/api_docs.php
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request
import uuid

API_URL = "https://img.scdn.io/api/v1.php"

# Uploads are rate-limited per client IP: 5 per 5 seconds, 120 per 60 seconds.
MIN_INTERVAL_SECONDS = 1.2
RATE_LIMIT_WAIT_SECONDS = 5
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 60

# Without outputFormat the host converts static images to WebP; asking for the
# source's own format keeps the image the author supplied.
OUTPUT_FORMAT_BY_EXT = {
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".gif": "gif",
    ".webp": "webp",
}

CONTENT_TYPE_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class HostingError(Exception):
    """The host did not return a URL for an image."""


class ImageHost:
    """Uploads images one at a time, paced to the host's rate limit."""

    def __init__(self, ssl_context=None):
        self._ssl_context = ssl_context
        self._last_request = 0.0
        self._unreachable = None

    def upload(self, path):
        """Upload one image file and return its public URL."""
        if self._unreachable:
            raise HostingError("host unreachable: %s" % self._unreachable)

        ext = os.path.splitext(path)[1].lower()
        fields = {}
        if ext in OUTPUT_FORMAT_BY_EXT:
            fields["outputFormat"] = OUTPUT_FORMAT_BY_EXT[ext]
        with open(path, "rb") as fh:
            data = fh.read()
        body, content_type = _multipart(
            fields, os.path.basename(path), data,
            CONTENT_TYPE_BY_EXT.get(ext, "application/octet-stream"))

        for attempt in range(1, MAX_ATTEMPTS + 1):
            status, retry_after, payload = self._post(body, content_type)
            if status == 429 and attempt < MAX_ATTEMPTS:
                time.sleep(retry_after)
                continue
            break

        if payload.get("success") and payload.get("url"):
            return payload["url"]
        reason = payload.get("error") or payload.get("message") or "no URL in response"
        raise HostingError("HTTP %s: %s" % (status, reason))

    def _post(self, body, content_type):
        """Send one upload request; return (status, retry_after, payload)."""
        wait = self._last_request + MIN_INTERVAL_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)

        request = urllib.request.Request(
            API_URL, data=body, method="POST",
            headers={"Content-Type": content_type,
                     "User-Agent": "Mozilla/5.0 (qingyun-md-2-zhihu)"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS,
                                        context=self._ssl_context) as resp:
                status, headers, raw = resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            status, headers, raw = exc.code, exc.headers, exc.read()
        except urllib.error.URLError as exc:
            # A connection that cannot be made will fail the same way for
            # every image, so stop trying instead of timing out on each one.
            self._unreachable = exc.reason
            raise HostingError("host unreachable: %s" % exc.reason)
        except socket.timeout:
            raise HostingError("upload timed out after %ds" % TIMEOUT_SECONDS)
        finally:
            self._last_request = time.monotonic()

        try:
            retry_after = float(headers.get("Retry-After") or RATE_LIMIT_WAIT_SECONDS)
        except ValueError:
            retry_after = RATE_LIMIT_WAIT_SECONDS

        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            payload = {"error": raw[:200].decode("utf-8", "replace")}
        return status, retry_after, payload


def _multipart(fields, filename, data, file_content_type):
    """Encode form fields plus one `image` file as a multipart/form-data body."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append((
            '--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
            % (boundary, name, value)).encode("utf-8"))
    parts.append((
        '--%s\r\nContent-Disposition: form-data; name="image"; filename="%s"\r\n'
        'Content-Type: %s\r\n\r\n' % (boundary, filename, file_content_type)).encode("utf-8"))
    parts.append(data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary
