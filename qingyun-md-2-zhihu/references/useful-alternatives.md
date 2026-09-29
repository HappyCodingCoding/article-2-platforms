# Useful alternatives

Approaches that were tested and worked, but were still ruled out as the
skill's method for the step they apply to. Kept here instead of in
SKILL.md per this project's rule against carrying alternatives in a
skill's own instructions — SKILL.md should describe what the agent does,
not the options it considered.

## Choosing the browser driver (Step 4)

The chosen mechanism is capability-based: SKILL.md states once the browser
actions it needs, and `browser-drivers.md` maps them onto whichever driver the
current agent has — its own browser extension first, `bsk` for any agent with
a shell. Every option below reaches the user's real, logged-in browser without
launching a separate one.

### `bsk` as the only driver

Agent-neutral by construction, and verified end to end with three draft runs
on an earlier version of this skill. Ruled out as the only path because it
makes every user install a CLI, a browser extension and a file-URL permission
even when their agent already drives the browser through its own extension.
It stays in the selection table as the fallback for agents without one.

### The Claude-in-Chrome extension as the only driver

Works, needs no per-run interaction, and verified end to end. Ruled out as the
only path because it ties the skill to one agent harness.

### Per-agent copies of Steps 4–10

Detecting the agent and carrying a separate Step 4–10 for each would give
every driver exact instructions. Ruled out because those steps are long and
nearly identical across drivers — the Zhihu page logic never changes, only the
verbs that reach it — so the copies would drift apart and a fix to one would
silently miss the others.

### Chrome DevTools Protocol, direct

Verified end to end against a live Edge: the import, the title and the
structure check all ran, `navigator.webdriver` reads `false`, and the
User-Agent is the browser's genuine one — the cleanest detection posture of
anything tested, because nothing is launched with automation switches. It
also has no visibility guard, so hidden file inputs can be set without being
exposed first, and its `evaluate` does not share a global scope.

Reaching it takes one **one-time** switch: `edge://inspect/#remote-debugging`
→ *Allow remote debugging for this browser instance*. That setting persists
across restarts (`devtools.remote_debugging.user-enabled` in `Local State`),
and it is the only way to get CDP onto the default profile — since Chrome 136
a `--remote-debugging-port` flag is ignored there.

Ruled out on one measured cost: **every fresh connection raises an
"Allow remote debugging?" dialog the user must click.** A single session can
cover a whole publish run, so the price is one click per run rather than per
action, but it forecloses unattended use.

Two details worth keeping if this is ever revisited:

- The HTTP discovery endpoints stay disabled in this mode — `/json/version`
  returns 404. The WebSocket URL has to be read from `DevToolsActivePort` in
  the browser's user-data directory, and its browser UUID changes on every
  restart, so it can never be cached.
- That file is **not** cleaned up on exit. It survives pointing at a dead
  port, so a connection attempt must be what proves CDP is live, not the
  file's presence.

### Playwright over CDP

Not a separate transport: `connectOverCDP` goes through the same endpoint and
raises the same per-connection dialog. Its API is markedly better —
`setInputFiles` works on hidden inputs by design, and its auto-waiting would
remove most of the polling this skill does by hand. Untested here. (Codex's
plugin exposes a Playwright handle through its own extension instead, which
avoids the dialog; that is the `codex-chrome` driver.)

### Copying the browser profile and launching a second browser

A dead end, recorded so it is not retried. Copying the profile directory and
launching the browser against the copy looks like it should carry the
session, and the cookie database does copy across intact when taken with
SQLite's backup API rather than `cp` (a plain copy is an inconsistent
snapshot the browser discards outright). But the second instance cannot
obtain the OS keychain key that encrypts the cookie values, so it prunes
every encrypted cookie on startup — measured at 65 Zhihu cookies in, 13 left,
and the auth token gone. The browser then mints fresh anonymous cookies and
the session is simply logged out.

This is not a macOS quirk. Windows applies App-Bound Encryption to the same
data, which is strictly harder to work around. Cookie material has to be
decrypted by the browser process that owns it, which is why every viable
option attaches to the running browser instead of copying from it.

### browser-use

An LLM-driven agent framework rather than a browser driver: a model
interprets the page and decides what to click. Ruled out on fit. This skill's
targeting is deliberately exact — file inputs are chosen by their `accept`
attribute precisely because description-based matching picks the wrong one
and fails like a success — and handing that decision back to a model
reintroduces the failure the exactness exists to prevent. It also needs its
own API key, and its anti-detection features are a hosted-service add-on that
would route the user's cookies through a third party.

## Automating the `bsk` setup gate (Step 4)

Both manual steps in `bsk`'s setup gate were investigated for automation.
Neither is worth doing, and the second should not be done at all.

### Force-installing the extension by enterprise policy

`ExtensionInstallForcelist` installs an extension silently. On Windows it can
be set under `HKCU` without administrator rights; on macOS it needs a plist
under `/Library`, so it needs `sudo`. The costs are that the browser then
reports itself as managed by an organization and the user can no longer
remove the extension.

Ruled out because it buys nothing on its own. The file-URL permission below
cannot be automated, so the skill still stops at its first upload — the
managed-browser badge is paid for with no working run gained.

### Writing the file-URL permission directly

The toggle is stored in the browser's `Secure Preferences`
(`edge_file_access_permission`, `newAllowFileAccess`), which is covered by a
per-entry HMAC and a `super_mac`. Writing it externally means forging that
tamper-detection, which exists specifically to stop software from granting an
extension local-file access behind the user's back. Not done, and not to be
added later.

The UI cannot be driven either: both `bsk` and CDP are refused on
`edge://`/`chrome://` pages, so the toggle cannot be clicked. No documented
policy maps to it — `ExtensionSettings` → `file_url_navigation_allowed`
governs navigating to `file://` URLs, not the host access the upload needs.

## Processing the markdown (Step 2)

The chosen mechanism hands Steps 1–3 of the old flow — fetching the source,
normalizing it, flattening lists, converting tables, downloading and hosting
images — to `qingyun-process-md` with `--platform Zhihu`. Alternatives for how
that processing itself is done are recorded in that skill's
`references/useful-alternatives.md`.

### Keeping a copy of the processing inside this skill

This skill used to carry its own `scripts/script.py` for the same work. Works,
and keeps the skill self-contained. Ruled out because the two copies would
drift: a fix to the normalizer or the Zhihu-specific passes in one would
silently miss the other.

## Getting hosted images into the import (Step 5)

The chosen mechanism imports markdown whose images are public URLs and lets
Zhihu's editor re-host them itself.

### Calling Zhihu's re-host endpoint from page JS

A hand-built `POST /api/uploaded_images` (`url` + `source=article`, with the
`_xsrf` token as `x-xsrftoken`) was rejected by Zhihu's gateway with `403` in
under 100 ms for both hosted URLs, before Zhihu ever tried to fetch them —
the editor's own requests carry headers a bare `fetch` lacks. Importing the
markdown lets the editor make the call itself.

## Image insertion (Step 8)

Both alternatives below were tried on an earlier, incorrect belief that
the dialog's file input couldn't be filled by automation (it can — see
`zhihu-editor-notes.md`, "上传"和"插入"是两件事"). They solve the same
problem — getting a local image into the editor — and share the same
weakness: both insert the image before its upload finishes, entirely
inside the editor, which is the window where an image can stall into
上传失败 if the next one starts too soon. The dialog flow SKILL.md
uses for images that kept a placeholder avoids that window: the image is already on Zhihu's CDN
by the time it's inserted. Everything specific to each mechanism follows.

### Clipboard paste

Put the image on the system clipboard, select the placeholder, send a
real paste keystroke:

```
osascript -e 'set the clipboard to (read (POSIX file "img-1.png") as «class PNGf»)'
```
then select the placeholder text and send `cmd+v`.

This inserts at the cursor and reaches the same `pic-private.zhihu.com`
CDN as the dialog flow — verified directly, not assumed. Ruled out as the
default because:

- The OS clipboard is shared, global state. Anything else running on the
  machine can overwrite it between the `osascript` call and the paste —
  observed in this session, where an unrelated action left the user's own
  chat text on the clipboard. A clobbered clipboard doesn't error, it
  silently pastes the wrong content.
- It destroys whatever the user had copied, as a side effect of a task
  unrelated to their clipboard.
- It's platform-specific (the `osascript` invocation is macOS-only).

Still a reasonable fallback if the dialog's file input ever becomes
unreachable (e.g. Zhihu redesigns the upload modal): select the
placeholder, re-copy the image immediately before each paste (never
copy all images up front), and wait for that image's `src` to become
`https://pic…` before moving to the next one.

### Local HTTP server + synthetic paste

Serve the images directory over `127.0.0.1`, then in page JS `fetch` each
image, wrap it in a `File`, put it in a `DataTransfer`, and dispatch a
synthetic paste:

```javascript
const r = await fetch('http://127.0.0.1:8899/img-1.png');
const dt = new DataTransfer();
dt.items.add(new File([await r.blob()], 'img-1.png', {type: 'image/png'}));
document.querySelector('.public-DraftEditor-content[contenteditable="true"]')
  .dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```

Also verified end to end — all 6 images in a test draft, correct
dimensions, correct order, on the CDN — once paced to wait for each
upload before starting the next. Ruled out as the default because:

- It needs page-JS execution for the insertion itself. The dialog flow
  only needs JS to locate the placeholder; the file-upload and click
  actions that actually place the image need no JS at all.
- It's an extra background process to start and tear down. A leaked
  server on the user's machine is a real, avoidable loose end.
- It depends on Chrome's Private Network Access policy continuing to
  allow an `https://` page to `fetch` `127.0.0.1`. That policy has been
  tightening across Chrome versions and could add a permission prompt or
  block it outright in a future release.

## Locating a file input (Steps 5 and 8)

### Describing it to `find`

The obvious approach, and the one that fails. `find` and `read_page` match on
an element's role, name and surrounding text, not on its attributes, and the
Zhihu editor carries four file inputs whose descriptions overlap: the 附件
attachment input (`.pdf,.md,.txt,…,.png,.jpg`), the image dialog's
(`image/webp,image/jpg,…`), the article-cover input (`.jpeg, .jpg, .png`) and
the MD/Doc import input (`.docx,.markdown,…`). Asking for "the image input"
or "the markdown input" returns whichever the description happens to fit —
observed in a real run: an image uploaded to the attachment input, which
turns the dialog's button into 添加文件 and inserts a file-name card rather
than a picture, with no error anywhere.

Ruled out in favour of selecting by `accept` in page JS and stamping the
winner with both a data attribute and a unique `aria-label` — a CSS selector
for drivers that take one, a name for drivers that search by description.
Either way the target is exact, and the snippet prints the `accept` it chose
so the decision is visible before anything is uploaded.

## Selecting the placeholder (Step 8)

The chosen mechanism clicks the tagged span, presses End, then Shift+Home, and
confirms the selection text before deleting anything.

### Triple-click

Worked under `claude-in-chrome` in a real run. Ruled out for two reasons. It
needs the page to hold focus: a driver's own click grants that (measured —
`document.hasFocus()` becomes true even while the tab stays hidden), but a
window driven with focus withheld, such as `bsk`'s `--no-focus` Agent Window,
selects nothing at all. And the selection it makes can include the
placeholder's trailing line break (`【IMG-N】\n`), so Backspace removes
the whole paragraph instead of leaving an empty one. Keyboard selection
behaves the same on every driver.

### Resolving the image input once, before the loop

Open the dialog once, tag its file input, press Escape, and reuse the tag for
every image — the input is the same element each time the dialog reopens.
Tried in a real run and dropped: the extra open-and-close cycle is one more
chance for a half-closed modal to eat the next click, and in that run the
triple-click that followed landed on the page's bottom bar instead of the
placeholder. Opening the dialog per image, after the cursor is parked, costs
one tagging snippet each time and leaves no modal state between images.

## Getting the upload dialog to react (Step 8)

### Dispatching the `change` event by hand

Tried in a real run and ruled out. The file-upload tool fires the input's
change handler itself; the dialog is merely slow to show 已上传 N 张图片, which
reads like nothing happened. Dispatching a `change` event in page JS to nudge
it makes the handler run a second time, and the image is inserted twice.

The duplicate is cheap to clean up — the figure's hover **×** removes it, and
the neighbour check catches it immediately — but the fix is to wait and read
the dialog again. Later images in that same run went in cleanly with no
dispatch at all.

## Recovering from a misplaced image (Step 8)

### Undo, then retry the same placeholder

Tried in a real run and ruled out. The placeholder is deleted before the
upload begins, so by the time an insert goes wrong the anchor is already
gone; Draft.js's undo restores the text of the block but not the caret, and
the retry then inserts at whatever the cursor drifted to. In that run image 1
ended up after the first paragraph instead of the fourth, and every check
that existed at the time — image count, CDN src, no placeholders remaining,
server `state: draft` — passed.

The skill rebuilds instead: clear the body, re-import, run the loop again.
Consistent with the existing rule that a draft in a bad state is easier to
rebuild than to repair.

### Rebuilding when the placeholder's paragraph collapses

When Backspace removes the placeholder's whole paragraph instead of leaving
it empty, a rebuild would be safe, but it is not needed: nothing has been
inserted yet, and both neighbours were recorded in step 1. The skill instead
clicks on the first line of the following block, presses Home then Enter to
push that block down, moves up into the new empty block, and checks that it
sits between the recorded neighbours with the caret in it. Rebuilding stays
the fix once an image has actually gone in at the wrong place.

### Recreating the block from the preceding block with End then Enter

Worked in a real run, but only because the preceding paragraph fit on one
line. `End` moves to the end of the visual line, not the end of the block, so
on a wrapped paragraph Enter splits the author's text mid-sentence. Starting
from the block below avoids this: the caret sits on its first line, where
`Home` and the block start coincide.


## Known limits of Step 7

- **Step 7's DOM mapping was verified against one article's block shapes.**
  Headings are counted by `qingyun-process-md` but not compared, because this
  skill strips the article's only heading to use as the title.
