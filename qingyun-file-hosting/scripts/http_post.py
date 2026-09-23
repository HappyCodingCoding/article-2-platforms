"""Sends one multipart/form-data upload request and returns the reply text.

Called by providers.py for uploads, and by script.py to take the proxy out
of the path for the retry lap.
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

# The timeout grows with the request's size. The base covers what every
# upload pays whatever its size: connecting, and waiting for the host to
# store the file and reply — picrd has been seen to take up to 21 s to reply
# for a 43 KB image. The per-MB part covers sending the bytes, at a
# floor of about 250 KB/s, half the slowest speed measured from this machine
# (0.45-1.4 MB/s). The cap stops an upload that is moving but crawling; it
# still lets Litterbox's 1 GB limit through at any speed above ~290 KB/s.
# The socket applies it to connecting, to sending the whole body (one
# sendall call), and to each wait for the reply.
TIMEOUT_BASE_SECONDS = 25
TIMEOUT_SECONDS_PER_MB = 4
TIMEOUT_MAX_SECONDS = 60 * 60
USER_AGENT = "Mozilla/5.0 (qingyun-file-hosting)"

# build_opener() keeps the default handlers except the ones passed in. Both
# openers carry the certifi SSL context in their HTTPS handler, since
# OpenerDirector.open() takes no context= argument. The proxied one also
# keeps the default proxy handler, which follows the environment or system
# proxy settings; the direct one replaces it with an empty one.
_PROXIED_OPENER = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=_SSL_CONTEXT))
_DIRECT_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=_SSL_CONTEXT))

# A proxy can break TLS to some hosts while passing everything else, so
# script.py's retry lap calls bypass_proxy() to send its retries direct.
_opener = _PROXIED_OPENER


class TransportError(Exception):
    """The request never produced a normal reply: a network or HTTP error."""


def proxy_in_use():
    """Whether requests currently go through a proxy."""
    proxies = urllib.request.getproxies()
    return _opener is _PROXIED_OPENER and ("https" in proxies or "http" in proxies)


def bypass_proxy():
    """Send every later request direct, ignoring any configured proxy."""
    global _opener
    _opener = _DIRECT_OPENER


def post_files(url, fields, file_field, paths, user_agent=USER_AGENT):
    """POST form fields plus every file in `paths` under `file_field`.

    Returns the reply body as stripped text. Raises TransportError on a
    network failure or an HTTP error status. `user_agent` is for a host
    whose API asks clients to identify themselves in its own format.
    """
    body, content_type = _multipart(fields, file_field, paths)
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": content_type, "User-Agent": user_agent})
    try:
        with _opener.open(request, timeout=timeout_for(len(body))) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace").strip()
        raise TransportError("HTTP %s%s" % (exc.code, ": " + detail if detail else ""))
    except urllib.error.URLError as exc:
        raise TransportError("network error: %s" % exc.reason)
    except OSError as exc:  # timeouts, resets and TLS failures mid-transfer
        raise TransportError("network error: %s" % exc)
    return raw.decode("utf-8", "replace").strip()


def timeout_for(size_bytes):
    """Seconds to allow a request of `size_bytes` before giving up on it."""
    seconds = TIMEOUT_BASE_SECONDS + TIMEOUT_SECONDS_PER_MB * size_bytes / (1024 * 1024)
    return min(seconds, TIMEOUT_MAX_SECONDS)


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
