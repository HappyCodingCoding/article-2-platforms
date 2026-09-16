# Browser drivers

Step 4 of SKILL.md drives the user's own logged-in browser through exactly one
driver per run. This file is where that choice is made and where each driver's
setup and verbs live; SKILL.md's steps are written against the capabilities
below and never name a driver's tools directly.

Every driver here attaches to the browser the user already has open. None of
them launches a separate browser, copies a profile, or needs a debug port —
see `useful-alternatives.md` for why those were ruled out.

## Choosing a driver

Start from what this agent can drive a browser with itself, not from a fixed
list. In order:

1. **Look through your own capabilities** for browser control — tools whose
   names carry `browser`, `tab`, `page`, `chrome` or `computer`, a bundled
   browser plugin, or an attached browser MCP server. The table below names the
   ones already identified; an agent missing from it may still have one.
2. **Hold the candidate against the capability checklist in SKILL.md Step 4.3.**
   It qualifies only if it can open or reuse a tab in the user's own logged-in
   browser, run page JS and return its value, click and press keys with real
   input, put a local file into a file input without a native picker, and take
   a screenshot.
3. **Fall back to `bsk`** when the agent has no browser capability of its own,
   or its capability fails the checklist, and it can run shell commands.
4. Otherwise stop and tell the user which capability is missing.

Prefer the agent's own driver: it is already attached to the browser the user
is logged into, and it costs no extra install. `bsk` is the fallback, not the
default.

| Agent | Its own driver | Status |
|---|---|---|
| Claude Code (CLI, desktop app, IDE extensions) | `claude-in-chrome` | verified — see its section |
| Codex (CLI or app) | `codex-chrome`, the bundled `browser` plugin | documented, unverified |
| Doubao / DoubaoWork (豆包) | ships its own browser (`Doubao Browser`) and an MCP helper | unverified — check your own tool list for a browser tool or browser MCP server before falling back |
| QwenWork / QoderWork (通义 / Qoder) | MCP-capable; QoderWork also ships a Chrome extension | unverified — same check |
| Any agent with unrestricted desktop control (computer use) | its computer-use tools, driving the browser window on screen | unverified — but the only class that makes the page genuinely visible; see its section |
| Any agent that can run shell commands | `bsk` | verified — see its section |
| An agent with neither a browser capability nor a shell | none | stop and tell the user |

| Driver | Status |
|---|---|
| `claude-in-chrome` | Verified 2026-09-15: image-hosting import plus a manual HEIC insert, checked against the server draft (that run selected the placeholder by triple-click; the keyboard selection SKILL.md now uses has not been re-run on this driver). |
| `codex-chrome` | Not verified with this skill. The verbs below come from the plugin's own documentation; confirm them against the docs Codex loads at runtime before relying on them. |
| `bsk` | Verified 2026-09-15 with the current SKILL.md: image-hosting import, keyboard selection, and a manual HEIC insert, checked against the server draft. Both uploads needed the make-visible step below, and the final save needed the Agent Window brought to the front. |

## Capability map

| Capability | `claude-in-chrome` | `codex-chrome` | `bsk` |
|---|---|---|---|
| Open or reuse the editor tab | `tabs_context_mcp` (`createIfEmpty: true`), then `navigate` | `browser.user.openTabs()` + `browser.user.claimTab(tab)` to reuse a tab, else open a new tab | `bsk session start`, then `bsk navigate <url> --session <id>` |
| Run page JS, get the value | `javascript_tool` | Playwright evaluation on `tab.playwright` | `bsk evaluate '<snippet>' --session <id>` |
| Real click | `computer` `left_click` with a `ref` or coordinates | Playwright locator `.click()` | `bsk click --selector '<css>' --session <id>` |
| Real keys | `computer` `key` — `End`, `shift+Home`, `Backspace`, `Escape`, `Enter`, `ArrowUp` | Playwright keyboard press | `bsk press End --session <id>`; `bsk press Home --modifiers shift --session <id>` |
| File into an `<input type="file">` | `find` the tagged `aria-label`, then `file_upload` with that ref | `waitForEvent("filechooser")`, click the input's locator, `chooser.setFiles([absPath])` | `bsk upload --selector 'input[data-zh-input="…"]' --file <path> --session <id>` |
| Screenshot | `computer` `screenshot` | the plugin's screenshot capability | `bsk screenshot --out <path> --session <id>` |
| Ask the human | the agent's own question tool | the agent's own question tool | `bsk request-help --prompt '…' --session <id>` |
| Bring the page into view | none of its own — escalate (below) | `(await browser.capabilities.get("visibility")).set(true)` | `bsk tab select <tab-id>` for a background tab; escalate when the window itself is covered |
| End the session | close the tabs you created (`tabs_close_mcp`) | close or release the tabs you opened or claimed | `bsk session stop <id>` |

## `claude-in-chrome` — Claude Code

**Setup gate.** Load the tools in one `ToolSearch` call —
`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch`
— and confirm `tabs_context_mcp` answers. The prefix is `mcp__claude-in-chrome__`
throughout; a similarly named browser server (the desktop app's own Browser
pane) may also be connected, and its tools act on a different, non-logged-in
browser.

**Pitfalls.**

- A `ref` returned by `find` cannot be used by a later action in the same
  `browser_batch`. Find in one call, act in the next.
- Coordinate clicks use the screenshot's frame, which can differ from the
  page's CSS viewport: multiply page coordinates by `frameWidth / innerWidth`.
  Prefer clicking a `ref` or a tagged element.
- This driver attaches to whichever Chromium browser the extension is connected
  to, which is often Edge rather than Chrome. `list_connected_browsers` reports
  only a generic name ("Browser 1"), so read the brand from the page instead —
  `navigator.userAgentData.brands` — and name that browser in every request you
  make of the user.
- **A tab this driver opens starts as a background tab.** `tabs_context_mcp`
  (`createIfEmpty: true`) and `tabs_create_mcp` put it in a window without
  activating it, so its page reports `visibilityState: 'hidden'` even when that
  window is one the user can see. Nothing here can activate it: there is no
  select/foreground tool, `computer` acts only inside the page, and
  `window.focus()` from the page is a no-op (verified — it returns without
  error and the page stays hidden). Ask the user to click that tab, then wait
  for `visible`. Left hidden, script calls time out while the page looks fine
  to the user — observed twice in one run.
- Closing the group's last tab removes the group. To replace a stuck tab,
  create the new tab in one call and close the old one in a later call.
- `file_upload` fires the input's change handler itself.

**End.** Close the tabs you created once Step 9 has passed.

## `codex-chrome` — Codex

Codex drives Chrome through its bundled `browser` plugin: the agent works in a
persistent Node REPL with `agent.browsers`, per-tab `tab.playwright` handles,
and screenshots.

**Setup gate.**

1. In the Codex app, open **Plugins**, add **Chrome**, and follow its setup,
   which installs the Chrome Web Store extension and grants its permissions.
2. For uploads, enable **Allow access to file URLs** on the extension: open
   `chrome://extensions` (or `edge://extensions`), click **Details** under the
   ChatGPT browser extension, and turn the toggle on. Without it every upload
   in Steps 5 and 8 fails.
3. Allow `zhuanlan.zhihu.com` when Codex asks for site access, and approve the
   upload confirmations it raises.

**Driving notes.**

- The REPL keeps state between calls, which is one reason every SKILL.md
  snippet is a self-contained function.
- Uploads go through the file chooser: start `waitForEvent("filechooser")`
  before clicking the tagged input's locator, then `setFiles` with absolute
  paths. `setInputFiles` is not exposed.
- The plugin keeps the browser in the background by default, so Step 4's
  visibility gate fails until you show it:
  `(await browser.capabilities.get("visibility")).set(true)`.
- Do not `goto` the URL a tab is already on — that reloads it and can discard
  unsaved editor state. Reload deliberately with `tab.reload()`.

**End.** Close or release the tabs you opened or claimed once Step 9 has passed.

## `bsk` — any agent with a shell

`bsk` (Tencent BrowserSkill) runs automation inside an isolated **Agent
Window** of the user's own logged-in Chromium browser, driven from the command
line, so it works for any agent that can run shell commands.

**Setup gate.** Check these in order and stop at the first failure.

1. **The CLI.** If `bsk --version` fails, install it (no sudo, writes to
   `~/.local/bin`):

   ```
   curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh     # macOS / Linux
   irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex          # Windows
   ```

2. **The extension.** `bsk doctor` exits `0` when everything is connected; its
   `extension connected` line is the one that matters. If it is not connected,
   the extension has to be added from the browser's store — this cannot be
   automated, because the store's confirmation sits outside the page. Open the
   right store page so the user is one click away, then ask them to add it:

   - Edge: `https://microsoftedge.microsoft.com/addons/detail/browserskill/emacgiaaaiojkkpkddmmdfhmokgmnikg`
   - Chrome and other Chromium browsers: `https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi`

3. **The session.** `bsk session start` prints a four-letter token; that token
   is the `--session` value for every later command. **Do not pass
   `--no-focus`** — a hidden Agent Window reports `visibilityState: 'hidden'`
   and performs no text selection. With several browsers connected, pick one
   with `bsk browsers` and `--browser <id>`.

4. **The file-URL permission.** Uploads fail without it, and `bsk doctor` does
   not check it. Probe it with a throwaway input on a blank page and any small
   local file:

   ```
   bsk navigate "https://example.com" --session <id>
   bsk evaluate "(()=>{const i=document.createElement('input');i.type='file';i.id='probe';i.style.cssText='position:fixed;top:10px;left:10px;width:220px;height:36px;z-index:9999';document.body.appendChild(i);return 1})()" --session <id>
   bsk upload --selector "#probe" --file <any-local-file> --session <id>
   bsk evaluate "(()=>document.getElementById('probe').files.length)()" --session <id>
   ```

   `1` means uploads work. `Not allowed`, or `0`, means the permission is off:
   ask the user to open `edge://extensions/` (or `chrome://extensions/`), find
   **BrowserSkill**, click **Details**, and turn on **Allow access to file
   URLs**. Toggling it restarts the extension and kills every session, so
   start a new one afterwards.

**Driving notes.**

- `bsk evaluate` awaits a returned promise by default and prints the value.
  Snippets share one global scope across calls. Each call has a 30-second RPC
  timeout (`--timeout` raises it), so keep a polling loop inside a snippet well
  under that, or poll with repeated short reads instead.
- `bsk upload` refuses an element it cannot see, and every file input on the
  Zhihu page is `display:none`. If it reports the target is not visible, make
  the tagged input visible in the tagging snippet —
  `input.style.cssText = 'position:fixed;left:10px;top:10px;width:220px;height:36px;opacity:1;z-index:99999;display:block;visibility:visible'`
  — and upload again.
- The Agent Window can end up behind other windows. Its page then reports
  `visibilityState: 'hidden'`, and once it has been hidden for a while a
  change — observed with inserted images — may not be saved until the page is
  visible again. `bsk tab select` makes a background tab visible inside the
  Agent Window, but it does not raise a window that other windows cover: ask
  the user to bring it to the front. The Agent Window opens in whichever browser
  `bsk browsers` lists, which may be Edge rather than Chrome, and closing it
  ends the session.
- Keys: `bsk press End`, `bsk press Backspace`, `bsk press Escape`,
  `bsk press Enter`, `bsk press ArrowUp`, and Shift+Home as
  `bsk press Home --modifiers shift`, each with `--session <id>`.
- Clicks: `bsk click --selector '[data-zhtext="N"]' --session <id>`. SKILL.md
  tags its targets in page JS, so CSS selectors are preferred over `bsk
  observe` refs, which go stale whenever the DOM changes.
- Login walls and captchas: `bsk request-help --prompt '…' --session <id>`,
  and resume only on `continued` or `completed`.
- Check the latest `bsk <command> --help` for flags rather than guessing.

**End.** `bsk session stop <id>` once Step 9 has passed, and on failure paths
too.

## If the page stalls — making it visible

A driver-opened tab is hidden by default and runs fine that way: a driver click
gives the page focus, which is what selection, typing and page JS need. Do not
interrupt the user to make it visible as a matter of course. Reach for this
only on a real symptom — page calls timing out, a selection coming back empty
after a driver click, or Step 9 showing the server copy missing the last change
while the editor holds it.

Keep the driver you chose — an extension driver is the efficient one: it
targets by selector, returns structured values from page JS, and batches
several actions per call, where desktop control needs a screenshot and fresh
coordinates for every step. Use desktop control for the single action an
extension driver cannot perform: clicking the tab to activate it. Escalate in
this order and stop at the first that works:

1. **The driver's own way**, from the capability map above — Codex's visibility
   capability, `bsk tab select` for a background tab.
2. **The agent's desktop control**, if it has one and it is allowed to click in
   a browser: one click on the tab in the browser window makes it the active
   tab, and the page becomes `visible`. Many harnesses forbid this — Claude
   Code grants browsers a read-only tier, so the click is refused there and you
   fall straight through to step 3.
3. **Ask the user** to click that tab, naming the browser you read from the
   page, and wait until `visibilityState` reads `visible`.

Do not switch drivers to solve visibility. Driving the whole run by desktop
control costs a screenshot per step and gives up the JS-derived checks in
Steps 7 and 9.

## Desktop control as the driver (computer use)

An agent that can click and type on the user's screen drives the browser as a
person does, which removes the whole class of visibility problems the other
drivers have: the tab it clicks becomes the active tab, so `visibilityState` is
`visible`, timers run at full rate, and Zhihu never holds a save. It is also
the only driver that can work a native file picker, so Step 5's and Step 8's
uploads need no hidden-input trick.

What it costs: it takes over the screen and the user's focus for the length of
the run, it works from coordinates and screenshots rather than selectors — so
it is slower and more fragile against layout shifts — and page JS may not be
available at all, which Steps 7 and 9 rely on. Check that before choosing it:
a driver with no way to run JS and return a value fails Step 4.3.

It is also frequently unavailable for this purpose. Claude Code's computer use
grants browsers a read-only tier — screenshots are allowed, clicks and typing
are refused — so it cannot drive Edge or Chrome there, and `claude-in-chrome`
remains that harness's driver. Other harnesses may grant full control; confirm
by attempting one click, not by assuming.

## Agents without a documented driver

Doubao / DoubaoWork, QwenWork and QoderWork were inspected on one machine
(2026-09-16) but never driven by this skill. What is known: Doubao and
DoubaoWork bundle their own Chromium browser (`Doubao Browser.app`) and an MCP
helper; QwenWork and QoderWork carry MCP support, and QoderWork ships a Chrome
extension of its own. Any of those could satisfy the checklist.

So when running in one of them, inventory your own tools first — a browser tool
or an attached browser MCP server — and test it against Step 4.3 before
deciding. Two constraints apply whatever you find: the browser must be the one
the user is logged into Zhihu on, and the driver must be able to set a file
input without opening a native picker, which is what usually rules a capability
out. If nothing qualifies and the agent can run shell commands, use `bsk`;
otherwise stop and tell the user which capability is missing.
