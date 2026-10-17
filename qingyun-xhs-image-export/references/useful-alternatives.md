# Useful alternatives

Approaches that were tried for this skill and either worked but were ruled
out, or are worth knowing about when the chosen method stops working. Kept
here instead of in SKILL.md, which describes only what the agent does.

## Getting the image bytes out of the page (Step 7)

The chosen method packs the images into `window.name` and navigates the same
tab to a local receiver page, which posts them to the script same-origin. It
needs no permission, extension or user action and works on every driver that
can navigate a tab. Its cost is that the tab leaves the publish page, so the
images must be re-rendered (open the draft, click 下一步) for another export.

### Return the bytes through the driver's JS result

Page JS can return each image as a base64 string, which the agent then
writes to disk. Works on any driver, but a 1440×2400 card is about
400–500 KB, so a seven-card note puts several megabytes of base64 through
the agent's context. Ruled out for cost; acceptable for a single image.

### Browser download

An `<a download>` click on each `blob:` URL saves it through the browser's
own download flow. In Claude Code's built-in browser pane no file landed
anywhere on disk. In a regular Chrome or Edge it saves to the browser's
download folder (or asks where, depending on its settings), after which the
files have to be found and moved. Ruled out because where the files land is
not under the skill's control.

### A browser extension with `chrome.downloads`

A small Manifest V3 extension can read the `<img>`s on the publish page and
save them with `chrome.downloads.download`, into any subfolder of the
download folder. Reliable and needs no agent, but it is a separate thing to
install and maintain, cannot write outside the download folder without
native messaging, and does not run in an agent's built-in browser.

## Rendering the cards without 下一步

The editor's cards are DOM (`.editor-item-new`, 900×1500 before scaling).
Cloning a card with every computed style inlined into an SVG
`<foreignObject>`, embedding the page's `@font-face` fonts as data URLs, and
drawing it to a canvas produces a PNG without leaving the editor. Ruled out
because it is a re-creation, not the file XHS publishes: the size differs
(900×1500 against XHS's 1440×2400) and fidelity depends on every style and
font being captured.

## Delivery routes that the page blocks

Tried from the publish page and blocked in Claude Code's built-in browser
pane (no CSP header is involved; the browser's local-network protections
stop them):

- `fetch` or XHR `POST` to `http://127.0.0.1:<port>`;
- image beacons (`new Image().src = 'http://127.0.0.1:…?d=…'`) carrying
  chunks of base64;
- a hidden `<iframe>` on the receiver page, fed by `postMessage`;
- `window.open` of the receiver page — it was not a popup but navigated the
  only tab away.

Injecting a third-party rendering library (html2canvas) from a CDN into the
Xiaohongshu page was refused by the agent's own safety checks.
