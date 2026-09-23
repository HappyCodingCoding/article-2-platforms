#!/usr/bin/env python3
"""Main script for the qingyun-file-hosting skill: uploads local files to a
public file host and prints their URLs.

Usage:
    python3 script.py <file> [<file> ...] [--host fallback|litterbox|catbox]
                      [--images-only | --any-file]
                      [--persistence temporary|permanent]

What it does:
    1. Checks every file exists. With --images-only (the default), also
       checks every file is an image, and stops before uploading anything
       if one is not.
    2. Builds the provider queue. --host fallback takes every provider in
       providers.PROVIDERS order that fits the other options: --any-file
       keeps only providers that accept any file type, --persistence
       permanent keeps only permanent ones. A named --host is the whole
       queue, and must fit the other options too.
    3. Walks the queue. At each provider, the files still waiting are
       checked against its limits (size, banned extensions); a file it
       cannot take waits for the next provider. The rest are uploaded, one
       per request or, for a provider that takes several per request,
       grouped under its count and total-size caps.
         - URL reply: the file is done.
         - Network or HTTP error: the provider is dropped for the rest of
           this lap, and its files wait for the next provider.
         - Any other reply: the file is not tried anywhere else, and the
           reply is reported as its error.
       If any file is still pending once every provider has had a turn, the
       whole queue runs one more time (a second lap) for the files still
       pending — so a file that hit a transient network/HTTP error gets one
       more turn at every provider, in the same order, instead of stopping
       at the end of the first lap. A file a provider explicitly rejected
       with a non-URL reply is not retried in the second lap: that reply is
       a definite answer, not a blip.
    4. Prints to stdout the URL for a single file, or a JSON array of URLs
       in input order (null for a file that failed) for several. Per-file
       progress and errors go to stderr.

Exit status: 0 when every file was uploaded, 1 when any file failed,
2 when the arguments are invalid and nothing was uploaded.
"""

import argparse
import json
import os
import sys

from providers import PROVIDERS, PROVIDERS_BY_NAME, RejectedError, TransportError

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".svg", ".ico", ".heic", ".heif", ".avif", ".jxl",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload files to a public file host and print their URLs.")
    parser.add_argument("files", nargs="+", help="local files to upload")
    parser.add_argument(
        "--host", default="fallback", choices=["fallback"] + list(PROVIDERS_BY_NAME),
        help="fallback tries each fitting provider in order until one succeeds")
    kind = parser.add_mutually_exclusive_group()
    kind.add_argument("--images-only", dest="any_file", action="store_false",
                      help="every file must be an image (default)")
    kind.add_argument("--any-file", dest="any_file", action="store_true",
                      help="allow any file type; only any-file providers are used")
    parser.set_defaults(any_file=False)
    parser.add_argument(
        "--persistence", default="temporary", choices=["temporary", "permanent"],
        help="permanent uses only providers that never expire uploads")
    return parser.parse_args()


def fail_usage(message):
    print("error: " + message, file=sys.stderr)
    sys.exit(2)


def check_files(paths, any_file):
    for path in paths:
        if not os.path.isfile(path):
            fail_usage("file not found: %s" % path)
    if not any_file:
        not_images = [p for p in paths
                      if os.path.splitext(p)[1].lower() not in IMAGE_EXTENSIONS]
        if not_images:
            fail_usage("not an image (pass --any-file to upload any file type): "
                       + ", ".join(not_images))


def mismatch(provider, any_file, persistence):
    """Why a provider does not fit the options, or None if it does."""
    if any_file and provider.accepts != "any":
        return "%s accepts images only, but --any-file was given" % provider.name
    if persistence == "permanent" and provider.persistence != "permanent":
        return "%s is temporary (uploads expire after %s), but --persistence " \
               "permanent was given" % (provider.name, provider.expiry)
    return None


def build_queue(host, any_file, persistence):
    if host != "fallback":
        provider = PROVIDERS_BY_NAME[host]
        reason = mismatch(provider, any_file, persistence)
        if reason:
            fail_usage(reason)
        return [provider]
    queue = [p for p in PROVIDERS if not mismatch(p, any_file, persistence)]
    if not queue:
        fail_usage("no provider fits these options")
    return queue


def batches(provider, indices, sizes):
    """Group file indices into requests under the provider's per-request caps."""
    batch, batch_bytes = [], 0
    for i in indices:
        full = (len(batch) >= provider.max_files_per_request
                or batch_bytes + sizes[i] > provider.max_request_bytes)
        if batch and full:
            yield batch
            batch, batch_bytes = [], 0
        batch.append(i)
        batch_bytes += sizes[i]
    if batch:
        yield batch


# A file still pending after one full pass through the queue gets exactly
# one more full pass (a "retry lap") before it is reported as failed.
MAX_LAPS = 2


def upload_all(paths, queue):
    """Walk the queue, up to MAX_LAPS times; return the URLs indexed like
    `paths` (None if failed)."""
    sizes = [os.path.getsize(p) for p in paths]
    urls = [None] * len(paths)
    errors = [[] for _ in paths]
    pending = list(range(len(paths)))

    for lap in range(1, MAX_LAPS + 1):
        if not pending:
            break
        if lap > 1:
            print("retrying %d file(s) from the top of the queue (lap %d of %d)"
                  % (len(pending), lap, MAX_LAPS), file=sys.stderr)
            for i in pending:
                errors[i] = []  # this lap's reasons replace the last lap's

        for provider in queue:
            eligible = []
            for i in pending:
                reason = provider.refusal(paths[i], sizes[i])
                if reason:
                    errors[i].append(reason)
                else:
                    eligible.append(i)

            for batch in batches(provider, eligible, sizes):
                try:
                    batch_urls = provider.upload([paths[i] for i in batch])
                except TransportError as exc:
                    note = "%s: %s" % (provider.name, exc)
                    print("  %s — dropping %s for this lap" % (note, provider.name),
                          file=sys.stderr)
                    for i in eligible:
                        if i in pending:
                            errors[i].append(note)
                    break
                except RejectedError as exc:
                    for i in batch:
                        errors[i] = [str(exc)]
                        pending.remove(i)
                        print("✗ %s — %s" % (paths[i], exc), file=sys.stderr)
                    continue

                expiry = " (expires in %s)" % provider.expiry if provider.expiry else ""
                for i, url in zip(batch, batch_urls):
                    urls[i] = url
                    pending.remove(i)
                    print("✓ %s → %s [%s%s]" % (paths[i], url, provider.name, expiry),
                          file=sys.stderr)

            if not pending:
                break

    for i in pending:
        print("✗ %s — no provider took it: %s" % (paths[i], "; ".join(errors[i])),
              file=sys.stderr)
    return urls


def main():
    args = parse_args()
    check_files(args.files, args.any_file)
    queue = build_queue(args.host, args.any_file, args.persistence)
    print("queue: " + " → ".join(p.name for p in queue), file=sys.stderr)

    urls = upload_all(args.files, queue)

    if len(urls) == 1:
        if urls[0]:
            print(urls[0])
    else:
        print(json.dumps(urls))
    sys.exit(0 if all(urls) else 1)


if __name__ == "__main__":
    main()
