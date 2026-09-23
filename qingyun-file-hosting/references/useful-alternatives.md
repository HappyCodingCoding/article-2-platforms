# Useful alternatives

Approaches that work but were ruled out as the skill's method.

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
