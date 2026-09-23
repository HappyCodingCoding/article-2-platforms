# Useful alternatives

Approaches that work but were ruled out as the skill's method.

## Catbox uploads

### Uploading with a userhash

Catbox accepts an optional `userhash` form field that ties the upload to a
Catbox account, so the file shows up in that account and can be deleted later.
Ruled out because anonymous uploads are enough for this skill, and a userhash
is an account credential the skill would have to keep out of transcripts
(e.g. by reading it from an environment variable).

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
