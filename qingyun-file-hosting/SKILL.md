---
name: qingyun-file-hosting
description: Uploads one or more local files to a public file host and returns their URLs — one URL for one file, a JSON array for several. Providers, most reliable first, are uguu (temporary, 3h, any file, up to 128 MB), kappa (temporary — keeps files for an unstated time — any file, up to 100 MiB), ImgBB (permanent, images only, up to 32 MB, needs the user's own API key), imgcdn (temporary, 14 days, images only, up to 20 MB), scdn (img.scdn.io; temporary, deleted after 60 days without a view, JPEG and GIF only, up to 5 MB), Catbox (permanent, any file, up to 200 MB), picrd (permanent, images only, up to 10 MB), Litterbox (temporary, 24h, any file, up to 1 GB) and, as a last-resort fallback, sxcu (permanent, images only, up to 95 MB). `--host fallback` (default) tries each fitting provider in turn, most reliable first, until one succeeds, running the whole queue a second time for any file still pending after a transient error before giving up on it — with the proxy bypassed on that second lap when one is in use; `--host <name>` uses only that one. `--images-only` (default) / `--any-file` sets which file types are allowed and which providers qualify; `--persistence temporary` (default) / `permanent` limits the queue to providers whose links never expire. ImgBB joins the fallback queue only when its key is set; `--host imgbb` without one asks the user for it. Every other host is anonymous — no account, no deletion afterwards. Triggers on "upload this file", "host this image", "give me a public link for", "图床", "上传文件", "file hosting", "catbox", "picrd", "imgbb", "imgcdn", "scdn", "img.scdn.io", "uguu", "kappa", "litterbox", "sxcu". Does not download, convert or compress files.
---

# File Hosting

Uploads local files to a public file host and hands back a URL for each, trying providers in a fallback queue until one takes the file.

## Usage

Callable by explicit options or by natural language: take the files from whatever paths the user gives, and infer the options from what they say (e.g. "a link that won't expire" → `--persistence permanent`; "upload this zip" → `--any-file`; "put it on catbox" → `--host catbox`). Name every inferred option before running. If an option could be read two ways, ask rather than guessing.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `<file> …` | option (required) | one or more local file paths | — | The files to upload, in the order their URLs are returned. |
| `--host` | option | `fallback` / `uguu` / `kappa` / `imgbb` / `imgcdn` / `scdn` / `catbox` / `picrd` / `litterbox` / `sxcu` | `fallback` | `fallback` builds a queue of every provider that fits the other options, ordered by stability and reliability (the Providers table, top first), and moves a file down the queue until a provider takes it; ImgBB is in it only when its API key is set. A named host is for a user who wants that provider specifically; the run fails rather than falling back if it cannot take the file. `imgbb` without a key stops before uploading so the user can supply one (Step 2). |
| `--images-only` / `--any-file` | flag pair | — | `--images-only` | `--images-only` requires every file to be an image, and qualifies every provider that accepts images, including those that take any file. `--any-file` allows any file type and qualifies only providers that accept any file type. |
| `--persistence` | option | `temporary` / `permanent` | `temporary` | `temporary` qualifies every provider, whether its links expire or not. `permanent` qualifies only providers whose links never expire — use it for links meant to stay up, such as ones published in an article. |

### Providers

Ranked by observed reliability, most reliable first — the order every fallback queue keeps. Hosts with no failed uploads in testing come ahead of those with some, ties broken by speed and by how steady the service looks. sxcu is the exception: it sits last as an extra fallback, reached only when every other fitting host has failed (see Gotchas for why).

| Provider | Persistence | Takes and serves unchanged | Max per file | Passed on |
|---|---|---|---|---|
| `uguu` | temporary — deleted after a fixed 3h | any file | 128 MB | `.exe` `.scr` `.jar` `.docx` `.html` `.bat` `.com` `.msi` `.svg` (refused) |
| `kappa` | temporary — retention not stated | any file, `.exe` `.html` `.svg` included | 100 MB | none found; every type tested was kept |
| `imgbb` | permanent — uploads land in the user's own ImgBB account | every other image type | 32 MB | non-images (refused); `.svg` `.tif` `.tiff` `.bmp` (served as JPEG), `.heic` `.heif` (served as AVIF) |
| `imgcdn` | temporary — deleted after 14 days | `.jpg` `.jpeg` `.png` `.gif` `.webp` | 20 MB | `.bmp` (served as PNG); every other type (refused) |
| `scdn` | temporary — deleted after 60 days without a view | `.jpg` `.jpeg` (5 MB), `.gif` (3 MB) | 5 MB | `.png` (served as a 256-colour PNG), `.bmp` `.tif` `.tiff` (served as PNG); every other type, `.webp` included (refused or untested) |
| `catbox` | permanent | any file | 200 MB | `.exe` `.scr` `.cpl` `.jar` `.doc*` (refused) |
| `picrd` | permanent | `.png` `.jpg` `.jpeg` `.webp` `.gif` | 10 MB | every other type (refused) |
| `litterbox` | temporary — deleted after 24h | any file | 1 GB | `.exe` `.scr` `.cpl` `.jar` `.doc*` (refused) |
| `sxcu` | permanent | `.png` `.jpg` `.jpeg` `.gif` `.tif` `.tiff`; `.webp` `.ico` (untested) | 95 MB | every other type, `.bmp` included (refused) |

A file a host would refuse, or would serve back in a different format, is passed on to the next host without being sent — so a file only ever lands where it is kept as uploaded.

The resulting queues (imgbb only when its API key is set):

| Options | Queue |
|---|---|
| `--images-only`, `--persistence temporary` (defaults) | uguu → kappa → imgbb → imgcdn → scdn → catbox → picrd → litterbox → sxcu |
| `--images-only`, `--persistence permanent` | imgbb → catbox → picrd → sxcu |
| `--any-file`, `--persistence temporary` | uguu → kappa → catbox → litterbox |
| `--any-file`, `--persistence permanent` | catbox |

Types some hosts pass on get shorter queues out of those:

| File type | temporary | permanent |
|---|---|---|
| `.png` `.webp` | uguu → kappa → imgbb → imgcdn → catbox → picrd → litterbox → sxcu | imgbb → catbox → picrd → sxcu |
| `.svg` | kappa → catbox → litterbox | catbox |
| `.tif` `.tiff` | uguu → kappa → catbox → litterbox → sxcu | catbox → sxcu |
| `.heic` `.heif` `.bmp` | uguu → kappa → catbox → litterbox | catbox |
| `.avif` `.jxl` | uguu → kappa → imgbb → catbox → litterbox | imgbb → catbox |
| `.ico` | uguu → kappa → imgbb → catbox → litterbox → sxcu | imgbb → catbox → sxcu |

With `--any-file`, types some any-file hosts refuse get shorter queues too:

| File type | temporary | permanent |
|---|---|---|
| `.exe` `.scr` `.jar` `.docx` | kappa | none |
| `.doc` `.docm` `.cpl` | uguu → kappa | none |
| `.html` `.bat` `.com` `.msi` | kappa → catbox → litterbox | catbox |

ImgBB's handling of `.ico` and `.jxl`, and sxcu's of `.webp` and `.ico`, are untested: if a link from it ends in a different extension than the file uploaded, it converted the file — add the type to `converted_extensions` in `providers.py`; if sxcu refuses one, remove it from sxcu's `allowed_extensions`.

Every upload is public: anyone with the link can open it. Uploads to every host but ImgBB are anonymous and cannot be deleted afterwards; ImgBB uploads belong to the user's account, where they can manage them.

The ImgBB key is the user's own credential. The script reads it from the `IMGBB_API_KEY` environment variable, or else from `~/.config/qingyun-file-hosting/imgbb.key`. It lives outside the project, so it is never committed; never repeat it back in chat or write it anywhere else.

## Workflow

### Step 1 — Resolve the files and options

Confirm each path exists, then state the resolved options and go straight to Step 2 — this step is a status line, not a question, and an invocation with no options given is a request to run with every default, not an invitation to pick one. Only stop and ask when something is actually wrong or genuinely ambiguous:
- a file is missing;
- `--any-file` is not given and a file is not an image (say which, and ask whether to switch to `--any-file`);
- the user's own wording conflicts with an option they also gave (e.g. they asked for a permanent link but also named a temporary `--host`).

When `--host fallback` and `--persistence temporary` are both in effect (the defaults), mention in the status line that the file will most likely land on a temporary host, since the most reliable hosts come first and the top two are temporary — Uguu (a fixed 3h) first, then kappa (an unstated time), imgcdn (14 days), scdn (60 days without a view) or Litterbox (24h) — and that `--persistence permanent` keeps it to hosts whose links never expire. This is context for the one line the user gets back, not a reason to pause: run with the default unless the user's own request called the file private, confidential, or otherwise not for public posting, in which case point out that every upload is public and cannot be deleted, and wait for a go-ahead instead of running.

### Step 2 — Upload (script)

Run:
```
python3 qingyun-file-hosting/scripts/script.py <file> [<file> ...] [--host <fallback|uguu|kappa|imgbb|imgcdn|scdn|catbox|picrd|litterbox|sxcu>] [--any-file] [--persistence permanent]
```
Omit each option that is at its default.

The script checks the files, builds the queue, and walks it. At each provider, a file over its size limit or with an extension it does not take is passed on to the next provider without being sent. A network or HTTP error drops that provider for the rest of this lap and passes its files on. A host that stops responding counts as a network error once the request's timeout runs out: 25 s plus 4 s per MB sent, capped at 60 minutes — about 26 s for a screenshot, 65 s for 10 MB, 14 minutes for 200 MB. A reply that is not a URL stops that file there — it is not tried on any other provider, even on a later lap — and the reply is reported as its error. Every provider currently takes one file per request, so several files are uploaded one after another.

If a file is still pending once every provider in the queue has had a turn, and it met a network or HTTP error on the way, the whole queue runs again from the top for it — one retry lap, a second turn at every provider in order, before it is reported as failed. When a proxy is in use, the retry lap goes direct, bypassing it: a proxy that breaks TLS to some hosts while passing everything else is a common cause of first-lap network errors. A file that was only passed on for its size or type is not retried: those checks come out the same every lap.

stdout holds the result: the URL for a single file, or a JSON array of URLs in input order, with `null` for a file that failed. stderr holds the queue, one line per file saying which provider took it (and when it expires), and the error for each file that failed. Exit status is `0` when every file was uploaded, `1` when any failed, `2` when the arguments were invalid and nothing was uploaded, and `3` when `--host imgbb` was named without an API key and nothing was uploaded. In fallback mode a missing ImgBB key is not an error: stderr notes that ImgBB was left out, and the run goes on without it.

**If the exit status is `3`**, ask the user for their ImgBB API key: they get it by signing in at https://api.imgbb.com/ and clicking "Get API key". Tell them they can save it themselves to keep it out of the chat, with the command below; if they paste it instead, run the command for them with their key. Then re-run the same Step 2 command.
```
mkdir -p ~/.config/qingyun-file-hosting && (umask 077 && printf '%s' '<key>' > ~/.config/qingyun-file-hosting/imgbb.key)
```
If the user gives a key without being asked, save it the same way before running.

### Step 3 — Report

Give the user the URL(s) in input order, naming the provider for each and the expiry for a link from a temporary host. When a file landed on sxcu, say so, and that sxcu's terms grant it rights to reuse the file; when it landed on scdn, say that scdn lists uploads publicly (see Gotchas). For each failed file, quote its error — from the retry lap if it ran one, since that overwrites the first lap's reasons for a file that is still pending. If every provider failed with a network error on both laps, say the hosts look unreachable from this machine, through the proxy and without it, and ask the user to check their network rather than retrying again. See Gotchas for the failures worth naming to the user by their cause.

## Gotchas

**Litterbox blocks an IP that has just failed there.** Its firewall (BunkerWeb) answers `403 Forbidden` to the whole site, uploads and homepage alike, for an IP whose requests it dislikes — a run of rejected uploads is enough to trigger it. It says "try again in a few minutes" but has been seen to last over half an hour, well past this skill's one retry lap. A single dropped connection (not the WAF) usually clears by the retry lap on its own. If the error is still there on the retry lap too, report it and either retry later or name another host with `--host`.

**Catbox returns the same URL for a file it already has.** Uploading identical bytes twice gives one URL, so a re-run costs nothing — but the URL may also point at an older copy under that hash. A file that matters should be opened once to confirm the content is there.

**picrd allows 60 uploads per hour per IP.** Past that it answers `HTTP 429`, which passes the file on like any HTTP error. A large batch will spill over to the next host partway through; that is expected, not a fault.

**ImgBB rejects a wrong key with `HTTP 400` and `Invalid API v1 key.`** Being an HTTP error, it passes the file on like any other; with `--host imgbb` the file fails. Either way, tell the user their saved key was refused and ask for a fresh one, saved over the old one as in Step 2.

**A local proxy can break the download link uguu just returned, separately from the upload.** The retry lap's proxy bypass (Step 2) only covers the script's own upload requests; it does not cover fetching the link back afterward. This machine's proxy has been seen to fail TLS to uguu's `*.uguu.se` file subdomains specifically (the same failure mode already seen with img.scdn.io, litterbox and imgcdn). If verifying a `uguu` link fails right after a successful upload, retry that fetch directly (bypassing the proxy) before suspecting the upload itself.

**kappa never says how long it keeps a file.** Neither its site nor its API states a retention period, and its terms reserve the right to remove content at any time, so the skill counts it as temporary and never uses it for `--persistence permanent`. When a file lands there, say its lifetime is unknown. Its terms also require users to be 18 or older, and say third-party commercial use needs its prior approval.

**scdn shows uploads to the public, and reworks some.** An image uploaded to img.scdn.io can appear on its public explore page and random-image API, and the host AI-tags and describes it; keep private images off it with `--host`. Only JPEG and GIF come back unchanged — it reduces a PNG to 256 colours even when asked to keep PNG, so the skill passes PNGs on. Its size limit depends on the format: 5 MB for JPEG, 3 MB for GIF; larger files can have the connection dropped instead of an error. It allows 5 uploads per 5 seconds (120 a minute) — past that it answers `HTTP 429`. Its links now come from `img.cdn1.vip`, not `img.scdn.io`. On this machine, img.scdn.io has needed a proxy bypass before; the retry lap's direct route covers that.

**sxcu's terms take broad rights over what it hosts.** Its Terms of Service grant it an irrevocable, worldwide licence to anything uploaded, including the right to sell it and use it in advertising. That is why it sits last, reached only when every other fitting host has failed; tell the user whenever a file lands there. It also allows 4 uploads per minute — past that it answers `HTTP 429` like picrd — and refuses `.bmp` although its own docs list it.

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
