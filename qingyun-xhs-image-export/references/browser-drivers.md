# Browser drivers

Step 2 of SKILL.md drives a browser where the user is logged into
Xiaohongshu through exactly one driver per run. This file is where that
choice is made and where each driver's setup and verbs live; SKILL.md's
steps are written against the capabilities below and never name a
driver's tools directly.

This skill needs less than an editor-filling skill does: no file uploads
and no keyboard selection — only a tab it can navigate, page JS, a real
click, and a screenshot.

## Choosing a driver

1. **Look through your own capabilities** for browser control — tools whose
   names carry `browser`, `tab`, `page`, `chrome` or `computer`, a bundled
   browser plugin, or an attached browser MCP server. The table below names
   the ones already identified; an agent missing from it may still have one.
2. **Hold the candidate against the checklist in SKILL.md Step 2.3.**
3. **Check that the browser it reaches is logged into Xiaohongshu.** An
   agent can have more than one browser, each with its own logins — Claude
   Code has both Claude in Chrome (the user's Chrome or Edge) and the desktop
   app's own browser pane. Use the one the user names; otherwise, the one
   whose `creator.xiaohongshu.com` tab is already open; otherwise the agent's
   default. 草稿箱 lives in that browser's local storage, so the draft is only
   in the browser it was made in.
4. **Fall back to `bsk`** when the agent has no browser capability of its own
   and can run shell commands.
5. Otherwise stop and tell the user which capability is missing.

| Agent | Its own driver | Status |
|---|---|---|
| Claude Code desktop app | `claude-browser-pane` (the app's built-in browser) | verified 2026-10-17: a seven-card 长文笔记 draft opened from 草稿箱, rendered and saved at 1440×2400 |
| Claude Code (CLI, desktop app, IDE extensions) | `claude-in-chrome` | verified 2026-10-17 on Microsoft Edge: a one-card 长文笔记 draft opened from 草稿箱, rendered and saved at 1440×2400 |
| Codex (CLI or app) | `codex-chrome`, the bundled `browser` plugin | unverified with this skill |
| Any agent that can run shell commands | `bsk` | unverified with this skill |
| An agent with neither a browser capability nor a shell | none | stop and tell the user |

## Capability map

| Capability | `claude-browser-pane` | `claude-in-chrome` | `codex-chrome` | `bsk` |
|---|---|---|---|---|
| Open or reuse the tab, navigate it | `tabs_context`, then `navigate` | `tabs_context_mcp` (`createIfEmpty: true`), then `navigate` | `browser.user.openTabs()` + `claimTab(tab)`, else a new tab; `tab.goto(url)` | `bsk session start`, then `bsk navigate <url> --session <id>` |
| Run page JS, get the value | `javascript_tool` | `javascript_tool` | Playwright evaluation on `tab.playwright` | `bsk evaluate '<snippet>' --session <id>` |
| Real click (on an element SKILL.md tagged, e.g. `XHS-EXPORT-NEXT` / `[data-xhs-export="next"]`) | `find` the label, then `computer` `left_click` with that ref | `find` the label, then `computer` `left_click` with that ref | locator `[data-xhs-export="…"]` `.click()` | `bsk click --selector '[data-xhs-export="…"]' --session <id>` |
| Screenshot | `computer` `screenshot` | `computer` `screenshot` | the plugin's screenshot capability | `bsk screenshot --out <path> --session <id>` |
| File into the tagged `<input type="file">` (`--import` only) | none — see its section | `find` `XHS-EXPORT-IMPORT-INPUT`, then `file_upload` with that ref and the file's absolute path | `waitForEvent("filechooser")`, click the input's locator, `chooser.setFiles([absPath])` | `bsk upload --selector '[data-xhs-export="import"]' --file <path> --session <id>` |
| End | leave the tab on Xiaohongshu | close the tabs you created | close or release the tabs you opened or claimed | `bsk session stop <id>` |

## `claude-browser-pane` — Claude Code desktop app

The desktop app's own browser, shown in a pane beside the conversation. Its
tools are prefixed `mcp__Claude_Browser__` and are loaded already. It is a
separate browser from the user's Chrome, with its own logins: use it when the
user logged into Xiaohongshu there or asks for it.

**Browser not running.** `tabs_context` reports `browserOpen: false`, and
page calls fail with "No preview is open". `navigate` to
`https://creator.xiaohongshu.com/publish/publish?from=menu&target=image`
opens the pane on that page — no user action needed. The pane's logins and
草稿箱 survive it being closed.

**Tabs.** The pane usually has a single tab. When it shows another site,
open a new tab with `tabs_create` and `navigate` that one, so the user's page
is left alone.

**Setup gate.** Confirm the page is not a login screen.

**Pitfalls.**

- It has no file-upload action, so it cannot import a document itself (Step
  4.6). Step 4.3 then offers the user to import it with 从文件导入 in the pane
  themselves; for a hands-off import, use a driver that can upload (Claude in
  Chrome, `bsk`) in a browser logged into Xiaohongshu — the new note then
  lives in that browser's 草稿箱.
- `<a download>` clicks produce no file anywhere on disk, and the page cannot
  reach `127.0.0.1` by `fetch`, XHR, image beacons or an iframe — which is why
  Step 7 hands the images over through `window.name`.
- `window.open` from the page does not open a popup: it navigates the pane's
  only tab, losing the publish page. Never call it.
- A `ref` from `find` cannot be used by a later action in the same
  `browser_batch`. Find in one call, click in the next.

## `claude-in-chrome` — Claude Code

**Setup gate.** Load the tools in one `ToolSearch` call —
`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__javascript_tool`
(add `mcp__claude-in-chrome__file_upload` for `--import`) — and confirm
`tabs_context_mcp` answers.

**Browser not running.** With the browser closed the extension is offline:
`tabs_context_mcp` fails and `list_connected_browsers` lists nothing. Start
the browser from the shell, then poll `list_connected_browsers` every few
seconds for up to 30 seconds:

```
open -a "Google Chrome"        # macOS; "Microsoft Edge" for Edge
start chrome                   # Windows; msedge for Edge
google-chrome &                # Linux; microsoft-edge & for Edge
```

Use the browser the user names. Otherwise check which one carries the
extension — on macOS, `ls ~/Library/Application\ Support/Google/Chrome/*/Extensions ~/Library/Application\ Support/Microsoft\ Edge/*/Extensions`
for the Claude extension id `fcoeoabgfenejglbffodgkkbkcdhcgfn` — and ask when
both or neither do. If the browser starts but the extension never connects,
ask the user to sign in to the extension in that browser.

**Tabs.** The driver sees only the tabs in its own tab group, not the tabs
the user opened. A note the user has open in their own tab is out of reach:
open a new tab with `tabs_create_mcp` (or `tabs_context_mcp` with
`createIfEmpty: true` when there is no group yet) and `navigate` it.

**Pitfalls.**

- `javascript_tool` returns a promise as `{}` instead of awaiting it: put
  `await` in front of every async snippet — `await (async () => { … })()`.
- `javascript_tool` withholds any result that contains a URL query string or
  cookie-like data, replying `[BLOCKED: Cookie/query string data]`. Return
  `location.pathname`, never `location.href`.
- A tab this driver opens starts as a background tab, with
  `visibilityState: 'hidden'`. If page calls time out, ask the user to click
  that tab, naming the browser read from `navigator.userAgentData.brands` —
  the extension is often connected to Edge rather than Chrome.
- A `ref` from `find` cannot be used by a later action in the same
  `browser_batch`.

## `codex-chrome` — Codex

Codex drives Chrome through its bundled `browser` plugin: a persistent Node
REPL with `agent.browsers` and per-tab `tab.playwright` handles.

**Setup gate.** In the Codex app, open **Plugins**, add **Chrome**, follow its
setup, and allow `creator.xiaohongshu.com` when Codex asks for site access.
Allow `127.0.0.1` too: Step 7 navigates the tab to the local receiver.

**Browser not running.** If `browser.user.openTabs()` fails because Chrome is
closed, start it as the `claude-in-chrome` section shows, then retry.

**Driving notes.** The plugin keeps the browser in the background by default;
if page calls stall, show it with
`(await browser.capabilities.get("visibility")).set(true)`.

## `bsk` — any agent with a shell

`bsk` (Tencent BrowserSkill) drives an **Agent Window** of the user's own
logged-in Chromium browser from the command line.

**Setup gate.**

1. If `bsk --version` fails, install it (no sudo, writes to `~/.local/bin`):

   ```
   curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh     # macOS / Linux
   irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex          # Windows
   ```

2. `bsk doctor` must report `extension connected`. If not, open the store page
   so the user is one click away, and ask them to add it:
   - Edge: `https://microsoftedge.microsoft.com/addons/detail/browserskill/emacgiaaaiojkkpkddmmdfhmokgmnikg`
   - Chrome and other Chromium browsers: `https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi`
   A closed browser also shows up here as `extension` not connected: start the
   browser as the `claude-in-chrome` section shows, then run `bsk doctor`
   again before asking the user to install anything.
3. `bsk session start` prints the four-letter token used as `--session` from
   then on. The Agent Window has its own tabs but shares the browser's
   storage, so 草稿箱 shows the drafts made in that browser.

**Driving notes.** `bsk evaluate` awaits a returned promise and has a
30-second timeout per call (`--timeout` raises it); Step 7's snippet can take
a few seconds for a long note. Check `bsk <command> --help` for flags rather
than guessing.
