---
name: qingyun-file-hosting
description: Uploads one or more local files to a public file host and returns their URLs — one URL for one file, a JSON array for several. Providers are Litterbox (temporary, 24h, up to 1 GB) and Catbox (permanent, up to 200 MB), both accepting any file type. `--host fallback` (default) tries each fitting provider in turn until one succeeds, running the whole queue a second time for any file still pending after a transient error before giving up on it; `--host <name>` uses only that one. `--images-only` (default) / `--any-file` sets which file types are allowed and which providers qualify; `--persistence temporary` (default) / `permanent` limits the queue to providers whose links never expire. Anonymous uploads only — no account, no deletion afterwards. Triggers on "upload this file", "host this image", "give me a public link for", "图床", "上传文件", "file hosting", "catbox", "litterbox". Does not download, convert or compress files.
---

# File Hosting

Uploads local files to a public file host and hands back a URL for each, trying providers in a fallback queue until one takes the file.

## Usage

Callable by explicit options or by natural language: take the files from whatever paths the user gives, and infer the options from what they say (e.g. "a link that won't expire" → `--persistence permanent`; "upload this zip" → `--any-file`; "put it on catbox" → `--host catbox`). Name every inferred option before running. If an option could be read two ways, ask rather than guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `<file> …` | option (required) | one or more local file paths | — | The files to upload, in the order their URLs are returned. |
| `--host` | option | `fallback` / `litterbox` / `catbox` | `fallback` | `fallback` builds a queue of every provider that fits the other options, in the order Litterbox → Catbox, and moves a file down the queue until a provider takes it. A named host is for a user who wants that provider specifically; the run fails rather than falling back if it cannot take the file. |
| `--images-only` / `--any-file` | flag pair | — | `--images-only` | `--images-only` requires every file to be an image, and qualifies every provider that accepts images, including those that take any file. `--any-file` allows any file type and qualifies only providers that accept any file type. |
| `--persistence` | option | `temporary` / `permanent` | `temporary` | `temporary` qualifies every provider, whether its links expire or not. `permanent` qualifies only providers whose links never expire — use it for links meant to stay up, such as ones published in an article. |

### Providers

| Provider | Persistence | Accepts | Max per file | Refuses |
|---|---|---|---|---|
| `litterbox` | temporary — deleted after 24h | any file | 1 GB | `.exe` `.scr` `.cpl` `.jar` `.doc*` |
| `catbox` | permanent | any file | 200 MB | `.exe` `.scr` `.cpl` `.jar` `.doc*` |

Every upload is public and anonymous: anyone with the link can open it, and it cannot be deleted afterwards.

## Workflow

### Step 1 — Resolve the files and options

Confirm each path exists, then state the resolved options. When `--any-file` is not given, every file must be an image; if one is not, say which and ask whether to switch to `--any-file` instead of running. When `--host fallback` and `--persistence temporary` are both in effect, say that the file may land on Litterbox and expire in 24h. If the files are private, point out that the upload is public and cannot be deleted, and wait for a go-ahead.

### Step 2 — Upload (script)

Run:
```
python3 qingyun-file-hosting/scripts/script.py <file> [<file> ...] [--host <fallback|litterbox|catbox>] [--any-file] [--persistence permanent]
```
Omit each option that is at its default.

The script checks the files, builds the queue, and walks it. At each provider, a file over its size limit or with a refused extension is passed on to the next provider without being sent. A network or HTTP error drops that provider for the rest of this lap and passes its files on. A reply that is not a URL stops that file there — it is not tried on any other provider, even on a later lap — and the reply is reported as its error. Every provider currently takes one file per request, so several files are uploaded one after another.

If any file is still pending once every provider in the queue has had a turn, the whole queue runs again from the top for the files still pending — one retry lap, so a file that hit a transient network/HTTP error at one provider gets a second turn at every provider, in order, before it is reported as failed.

stdout holds the result: the URL for a single file, or a JSON array of URLs in input order, with `null` for a file that failed. stderr holds the queue, one line per file saying which provider took it (and when it expires), and the error for each file that failed. Exit status is `0` when every file was uploaded, `1` when any failed, and `2` when the arguments were invalid and nothing was uploaded.

### Step 3 — Report

Give the user the URL(s) in input order, naming the provider for each and the expiry for a Litterbox link. For each failed file, quote its error — from the retry lap if it ran one, since that overwrites the first lap's reasons for a file that is still pending. If every provider failed with a network error on both laps, say the hosts look unreachable from this machine — a local proxy is the usual cause — and ask the user to check it rather than retrying again. See Gotchas for the two failures worth naming to the user by their cause.

## Gotchas

**Litterbox blocks an IP that has just failed there.** Its firewall (BunkerWeb) answers `403 Forbidden` to the whole site, uploads and homepage alike, for an IP whose requests it dislikes — a run of rejected uploads is enough to trigger it. It says "try again in a few minutes" but has been seen to last over half an hour, well past this skill's one retry lap. A single dropped connection (not the WAF) usually clears by the retry lap on its own; if the error is still there on the retry lap too, or Catbox took the file instead, report it and either retry later or pass `--host catbox`.

**Catbox returns the same URL for a file it already has.** Uploading identical bytes twice gives one URL, so a re-run costs nothing — but the URL may also point at an older copy under that hash. A file that matters should be opened once to confirm the content is there.

## Output

One file:
```
https://files.catbox.moe/abc123.png
```

Several files:
```json
["https://litter.catbox.moe/abc123.png", null, "https://litter.catbox.moe/def456.jpg"]
```
