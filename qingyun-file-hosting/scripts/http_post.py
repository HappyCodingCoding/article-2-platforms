"""Sends one multipart/form-data upload request and returns the reply text.

Called by providers.py only.
"""

import mimetypes
import os
import ssl
import urllib.error
import urllib.request
import uuid

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None  # fall back to the interpreter's own CA store

# urllib applies this to each socket operation, not to the whole upload, so a
# large file that keeps making progress is not cut off.
TIMEOUT_SECONDS = 120
USER_AGENT = "Mozilla/5.0 (qingyun-file-hosting)"


class TransportError(Exception):
    """The request never produced a normal reply: a network or HTTP error."""


def post_files(url, fields, file_field, paths):
    """POST form fields plus every file in `paths` under `file_field`.

    Returns the reply body as stripped text. Raises TransportError on a
    network failure or an HTTP error status.
    """
    body, content_type = _multipart(fields, file_field, paths)
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": content_type, "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS,
                                    context=_SSL_CONTEXT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace").strip()
        raise TransportError("HTTP %s%s" % (exc.code, ": " + detail if detail else ""))
    except urllib.error.URLError as exc:
        raise TransportError("network error: %s" % exc.reason)
    except OSError as exc:  # timeouts, resets and TLS failures mid-transfer
        raise TransportError("network error: %s" % exc)
    return raw.decode("utf-8", "replace").strip()


def _multipart(fields, file_field, paths):
    """Encode form fields and files as a multipart/form-data body."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append((
            '--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
            % (boundary, name, value)).encode("utf-8"))
    for path in paths:
        filename = os.path.basename(path).replace('"', "_")
        file_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        parts.append((
            '--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
            'Content-Type: %s\r\n\r\n'
            % (boundary, file_field, filename, file_type)).encode("utf-8"))
        with open(path, "rb") as fh:
            parts.append(fh.read())
        parts.append(b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary
