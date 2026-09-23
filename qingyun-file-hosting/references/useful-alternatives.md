# Useful alternatives

Approaches that work but were ruled out as the skill's method.

## Proxy handling

### Retrying each failed request direct, straight away

When a request fails at the network level with a proxy configured, the same
request could be resent at once with the proxy bypassed, before the
provider counts as failed. Works, and catches a proxy that breaks TLS to one
host. Ruled out for speed: a request that timed out through the proxy could
then time out again direct, doubling the wait at that provider before the
queue moves on. The retry lap bypasses the proxy instead, so the first lap
reaches the next provider as soon as one fails.

## Hosts

### 0x0.st

Free, needs no account or key, takes any file up to 512 MiB, and keeps it for
30 days to a year depending on size — a temporary any-file host with a plain
`curl -F file=@...` API. Ruled out because its operator states on the
homepage that AI agents ("clankers") are not welcome, and this skill is run by
one. It is also a one-person service that blocks clients it dislikes by IP
and user agent, including any it judges to be posing as a browser.

### gofile.io

Free uploads of any file with no sign-up, through
`POST https://upload.gofile.io/uploadfile`. Ruled out because a free
upload returns only a `downloadPage` — a Gofile web page, not the file —
and direct links to the file are a Premium feature, so its links cannot be
embedded or imported like every other host's. Free storage also lasts only
10 days without a download before moving to cold storage, which only
Premium can restore. And each upload without a token creates a guest
account, which its API docs ask clients not to do per upload, so using it
properly means creating one guest account and keeping its token.

## Uguu uploads

### Uploading several files in one request

Uguu's `files[]` field accepts an array, and a two-file test request
returned both files' URLs in one response — real batching, unlike every
other provider here, which take one file per request. Ruled out for now:
the API docs don't state a limit on count or total size, and testing
higher counts risks tripping the "upload rate limiting" the project
documents without giving numbers for. `max_files_per_request` is left at
the default of 1 until that is worth testing.

### `?output=csv` / `text` / `html` / `gyazo`

Uguu's response format is chosen by a query parameter; the other formats
are plain text, HTML, CSV or a Gyazo-compatible reply. Ruled out in favour
of the default JSON, which every other JSON-replying provider here already
parses the same way (an object with the URL nested inside).

## kappa uploads

### Counting kappa as permanent

Its API returns no expiry and uploads stay reachable, so it could join the
`--persistence permanent` queue. Ruled out because nothing it publishes
promises that, and its terms let it remove content at any time; a link the
user publishes as permanent could vanish.

### `long-id=true`

A query parameter that makes the file id longer and harder to guess.
Ruled out because the other hosts' short links are no harder to guess, and
the skill's uploads are public by design.

### The bare `link` without an extension

The site ignores any extension on its links, so `link` alone works in a
browser. Ruled out in favour of appending the reply's `ext`, since some
readers, such as markdown importers, decide how to show a link by its
extension.

## scdn uploads

### `outputFormat=auto`

The default: every static image is turned into WebP, usually much smaller.
Ruled out because the skill only lands a file where it is kept as uploaded;
the format is asked for explicitly instead, and only JPEG and GIF survive
that unchanged.

### `storage_destination=telegram`

Stores the image on Telegram, which the site says does not actively delete
images, unlike its own storage's 60 days without a view. Ruled out because
nothing promises that either, so scdn stays temporary whichever storage is
used.

### Choosing a `cdn_domain`

The API lets the caller pick among seven CDN domains, including mainland
China ones. Ruled out in favour of the site's default, since no domain has
been tested to be steadier than another.

## sxcu uploads

### Ranking sxcu by reliability like the other hosts

sxcu uploaded every test file it accepts without a failure, which would rank
it among the hosts with no failures, near the top of the queue. Ruled out in favour of the last place in the
queue, because its Terms of Service take an irrevocable licence to resell
and advertise with anything uploaded; it is kept only as an extra fallback.

### `self_destruct` for 24-hour uploads

The field deletes the upload after 24 hours, which would make sxcu a
temporary host too. Ruled out for the same reason as picrd's `ttl_seconds`:
`--persistence temporary` means any host is acceptable, not that files
should expire.

### The viewer page instead of the file

Without `noembed`, the reply's `url` is a page with OpenGraph tags for
embedding in chat apps, not the file itself. Ruled out because every other
host returns a direct link to the file.

## Catbox uploads

### Uploading with a userhash

Catbox accepts an optional `userhash` form field that ties the upload to a
Catbox account, so the file shows up in that account and can be deleted later.
Ruled out because anonymous uploads are enough for this skill, and a userhash
is an account credential the skill would have to keep out of transcripts
(e.g. by reading it from an environment variable).

## picrd uploads

### `ttl_seconds` for self-expiring uploads

picrd deletes an upload after `ttl_seconds` when the field is sent, which
would let it serve as a temporary host too. Ruled out because
`--persistence temporary` means any host is acceptable, not that files should
expire, so there is no reason to give up a permanent link.

### `visibility=public`

Lists the upload on picrd's public feed. Ruled out in favour of the default
`unlisted`: a link that works for anyone who has it is all this skill needs.

## ImgBB uploads

### Passing the key as a script option

An `--imgbb-key <key>` option would need no file or environment variable.
Ruled out because the key would then appear in every command the agent runs —
in the transcript and in the process list — instead of once, when it is saved.

### Sending the key in the query string

The ImgBB docs show `?key=...` on the URL. Ruled out in favour of a form
field, which ImgBB accepts just the same and which keeps the key out of any
URL that gets logged.

## imgcdn uploads

### `format=json` and reading `image.url`

The default Chevereto reply is JSON carrying the direct link at `image.url`,
along with the viewer link, thumbnail, size and the guest expiration date.
Ruled out in favour of `format=txt`, which replies with the bare direct URL
on success and a bare error message on failure — the same shape Catbox and
Litterbox reply in, so no provider-specific parsing is needed.

## HTTP client

### `requests`

The library the reference catbox-upload skill uses; shorter multipart code.
Ruled out because the standard library's `urllib` does the same job without
adding a dependency to install.

## File-type selection

### A `--file-type any|image` option with aliases

A single option taking `any` (aliases `any-file`, `file`) or `image` (aliases
`just-image`, `only-image`, `image-only`). Ruled out in favour of the
`--images-only` / `--any-file` flag pair, which says the same with no values
to remember.

### Switching to `--any-file` automatically

When a non-image is passed without `--any-file`, the script could widen the
queue on its own. Ruled out so that a wrong file in an image batch is caught
instead of silently uploaded.
