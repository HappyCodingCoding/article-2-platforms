---
name: qingyun-file-hosting
description: Uploads one or more local files to a public file host and returns their URLs — one URL for one file, a JSON array for several. Providers are Catbox (permanent, any file, up to 200 MB), picrd (permanent, images only, up to 10 MB), imgcdn (temporary, 14 days, images only, up to 20 MB) and Litterbox (temporary, 24h, any file, up to 1 GB). `--host fallback` (default) tries each fitting provider in turn, most reliable first, until one succeeds, running the whole queue a second time for any file still pending after a transient error before giving up on it; `--host <name>` uses only that one. `--images-only` (default) / `--any-file` sets which file types are allowed and which providers qualify; `--persistence temporary` (default) / `permanent` limits the queue to providers whose links never expire. Anonymous uploads only — no account, no deletion afterwards. Triggers on "upload this file", "host this image", "give me a public link for", "图床", "上传文件", "file hosting", "catbox", "picrd", "imgcdn", "litterbox". Does not download, convert or compress files.
---

# File Hosting

Uploads local files to a public file host and hands back a URL for each, trying providers in a fallback queue until one takes the file.

## Usage

Callable by explicit options or by natural language: take the files from whatever paths the user gives, and infer the options from what they say (e.g. "a link that won't expire" → `--persistence permanent`; "upload this zip" → `--any-file`; "put it on catbox" → `--host catbox`). Name every inferred option before running. If an option could be read two ways, ask rather than guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `<file> …` | option (required) | one or more local file paths | — | The files to upload, in the order their URLs are returned. |
| `--host` | option | `fallback` / `catbox` / `picrd` / `imgcdn` / `litterbox` | `fallback` | `fallback` builds a queue of every provider that fits the other options, ordered by stability and reliability (the Providers table, top first), and moves a file down the queue until a provider takes it. A named host is for a user who wants that provider specifically; the run fails rather than falling back if it cannot take the file. |
| `--images-only` / `--any-file` | flag pair | — | `--images-only` | `--images-only` requires every file to be an image, and qualifies every provider that accepts images, including those that take any file. `--any-file` allows any file type and qualifies only providers that accept any file type. |
| `--persistence` | option | `temporary` / `permanent` | `temporary` | `temporary` qualifies every provider, whether its links expire or not. `permanent` qualifies only providers whose links never expire — use it for links meant to stay up, such as ones published in an article. |

### Providers

Ranked by stability and reliability, most reliable first — the order every fallback queue keeps.

| Provider | Persistence | Accepts | Max per file | Refuses |
|---|---|---|---|---|
| `catbox` | permanent | any file | 200 MB | `.exe` `.scr` `.cpl` `.jar` `.doc*` |
| `picrd` | permanent | `.png` `.jpg` `.jpeg` `.webp` `.gif` | 10 MB | every other type, other images included |
| `imgcdn` | temporary — deleted after 14 days | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` | 20 MB | every other type, other images included |
| `litterbox` | temporary — deleted after 24h | any file | 1 GB | `.exe` `.scr` `.cpl` `.jar` `.doc*` |

The resulting queues:

| Options | Queue |
|---|---|
| `--images-only`, `--persistence temporary` (defaults) | catbox → picrd → imgcdn → litterbox |
| `--images-only`, `--persistence permanent` | catbox → picrd |
| `--any-file`, `--persistence temporary` | catbox → litterbox |
| `--any-file`, `--persistence permanent` | catbox |

Every upload is public and anonymous: anyone with the link can open it, and it cannot be deleted afterwards.

## Workflow

### Step 1 — Resolve the files and options

Confirm each path exists, then state the resolved options. When `--any-file` is not given, every file must be an image; if one is not, say which and ask whether to switch to `--any-file` instead of running. When `--host fallback` and `--persistence temporary` are both in effect, say that the file may land on a temporary host if neither permanent host takes it — imgcdn (14 days) or Litterbox (24h). If the files are private, point out that the upload is public and cannot be deleted, and wait for a go-ahead.

### Step 2 — Upload (script)

Run:
```
python3 qingyun-file-hosting/scripts/script.py <file> [<file> ...] [--host <fallback|catbox|picrd|imgcdn|litterbox>] [--any-file] [--persistence permanent]
```
Omit each option that is at its default.

The script checks the files, builds the queue, and walks it. At each provider, a file over its size limit or with an extension it does not take is passed on to the next provider without being sent. A network or HTTP error drops that provider for the rest of this lap and passes its files on. A reply that is not a URL stops that file there — it is not tried on any other provider, even on a later lap — and the reply is reported as its error. Every provider currently takes one file per request, so several files are uploaded one after another.

If a file is still pending once every provider in the queue has had a turn, and it met a network or HTTP error on the way, the whole queue runs again from the top for it — one retry lap, a second turn at every provider in order, before it is reported as failed. A file that was only passed on for its size or type is not retried: those checks come out the same every lap.

stdout holds the result: the URL for a single file, or a JSON array of URLs in input order, with `null` for a file that failed. stderr holds the queue, one line per file saying which provider took it (and when it expires), and the error for each file that failed. Exit status is `0` when every file was uploaded, `1` when any failed, and `2` when the arguments were invalid and nothing was uploaded.

### Step 3 — Report

Give the user the URL(s) in input order, naming the provider for each and the expiry for a link from a temporary host. For each failed file, quote its error — from the retry lap if it ran one, since that overwrites the first lap's reasons for a file that is still pending. If every provider failed with a network error on both laps, say the hosts look unreachable from this machine — a local proxy is the usual cause — and ask the user to check it rather than retrying again. See Gotchas for the failures worth naming to the user by their cause.

## Gotchas

**Litterbox blocks an IP that has just failed there.** Its firewall (BunkerWeb) answers `403 Forbidden` to the whole site, uploads and homepage alike, for an IP whose requests it dislikes — a run of rejected uploads is enough to trigger it. It says "try again in a few minutes" but has been seen to last over half an hour, well past this skill's one retry lap. A single dropped connection (not the WAF) usually clears by the retry lap on its own. If the error is still there on the retry lap too, report it and either retry later or name another host with `--host`.

**Catbox returns the same URL for a file it already has.** Uploading identical bytes twice gives one URL, so a re-run costs nothing — but the URL may also point at an older copy under that hash. A file that matters should be opened once to confirm the content is there.

**picrd allows 60 uploads per hour per IP.** Past that it answers `HTTP 429`, which passes the file on like any HTTP error. A large batch will spill over to the next host partway through; that is expected, not a fault.

**imgcdn's own site calls its uploads permanent — guest uploads are not.** Its homepage says uploads never expire, but that holds for signed-in accounts; every API upload is a guest upload, and comes back set to expire 14 days later. Never describe an imgcdn link as permanent.

**imgcdn answers errors with HTTP 200.** A bad key, an oversized file and an unsupported type all come back as status 200 with a plain-text message, so they surface as a non-URL reply, not an HTTP error. `Invalid API v1 key.` means the published guest key in `providers.py` has been rotated: fetch the current one from https://imgcdn.dev/page/api and update it in the project.

## Output

One file:
```
https://files.catbox.moe/abc123.png
```

Several files:
```json
["https://files.catbox.moe/abc123.png", null, "https://s6.imgcdn.dev/Def456.jpg"]
```
