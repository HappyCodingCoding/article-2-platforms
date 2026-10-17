---
name: qingyun-xhs-image-export
description: Exports the card images Xiaohongshu (小红书 / Rednote) renders from a 写长文 (long-form) note’s 一键排版 card layout to a local folder, in the user's own logged-in browser, driven through whatever browser control the current agent has — its own browser extension or built-in browser (Claude in Chrome, the Claude desktop app's browser pane, Codex's Chrome plugin) or the agent-neutral `bsk` CLI. Opens the draft from 草稿箱 (or picks up the editor or publish page already open), clicks 下一步 so XHS renders the final images, then carries them out of the page into a folder through a local receiver run by its script. A note not yet laid out gets a template first: the agent applies the 一键排版 template and background the user picks from the list, or the one that suits the copy, or the user lays it out in the editor (`--template`). `--draft` picks the draft by title, `--output-dir` and `--prefix` set where and how the files are saved, `--driver` forces a browser driver. Never publishes, never deletes a draft. Triggers on "下载小红书配图", "导出小红书图片", "save the XHS card images", "download the images the XHS editor made", "xhs-image-export", or a request to get the 一键排版 card images out of the Xiaohongshu editor.
---

# Xiaohongshu Card Image Export

Gets the images Xiaohongshu renders from a 写长文 note laid out with 一键排版 — the same files that would be published — out of the browser and into a local folder, without publishing anything.

## Usage

Callable by explicit options or by natural language: infer `--draft` from a quoted or described note title, and `--output-dir` from any folder the user names. Name every inferred option before running. If two drafts match `--draft` equally well, list them and ask.

### Options

| Option | Type | Values | Default | Description |
|---|---|---|---|---|
| `--draft` | option | `auto` / `current` / a title or part of one | `auto` | Which note to export. `auto` uses the note already open in the XHS tab — in the card editor, the text editor or the publish page — when there is one with content, otherwise the only 长文笔记 draft in 草稿箱, and asks when there are several. `current` uses only the note already open and stops if there is none. A title opens the matching draft from 草稿箱 even when another note is open. |
| `--template` | option | `ask` / `agent` / `editor` / a template name, optionally with a background | `ask` | Only used when the note has not been laid out yet (Step 5.1); a note already in the card editor keeps its template. `ask` asks whether the agent applies a template or the user lays the note out in the editor, and for the agent route lists the templates and backgrounds in `references/templates.md` to choose from. `agent` lets the agent pick the template and background that suit the copy, without asking. `editor` leaves the layout to the user. A name such as `灵感备忘` or `灵感备忘 #4BA1FF` (or `灵感备忘 blue`, or `灵感备忘 2` for the second swatch) applies that template; without a background it gets the template's first swatch. |
| `--output-dir` | option | a folder path | `~/Downloads/xhs-images/<note title>/` | Where the images and `manifest.json` are written. Created if missing; files from an earlier export with the same names are overwritten. |
| `--prefix` | option | a file-name prefix | `xhs-card` | Files are saved as `<prefix>-<n>.<ext>`, numbered in card order from 1. |
| `--driver` | option | `auto` / `claude-in-chrome` / `claude-browser-pane` / `codex-chrome` / `bsk` | `auto` | How Step 2 reaches the browser. `auto` takes the running agent's first usable driver from `references/browser-drivers.md`. A named driver is for a user who prefers one; the run stops if it is unavailable. |

## Workflow

### Step 1 — Resolve the options

State `--draft`, `--template`, `--prefix` and `--driver` as resolved. When `--template` names a template, check it, and its background if given, against `references/templates.md` now; if either is not there, show the matching row or the list and ask, before touching the browser. `--output-dir` is stated in Step 6, once the note title is known; when the user named a folder, state it now.

### Step 2 — Choose the browser driver, then open Xiaohongshu

Every browser action from here to Step 9 goes through one driver. Choose it as `references/browser-drivers.md` describes, then use only that driver for the rest of the run.

1. **Identify the agent you are running in** and say which it is.
2. **Pick the driver.** With `--driver auto`, inventory the agent's own browser capabilities first and use one that passes the checklist below; fall back to `bsk` only when the agent has none. With a named `--driver`, use that one and stop if it is unavailable. State the chosen driver.
3. **Check the driver can do everything this skill needs.** It must be able to:
   - open or reuse a tab in a browser where the user is logged into Xiaohongshu, and navigate that tab to a URL;
   - run JavaScript in the page and return its value, awaiting a promise;
   - click an element with real input;
   - take a screenshot.

   If any is missing, stop and tell the user which one.
4. **Make sure the browser is running.** If the driver reaches no browser — the browser is closed, or its extension is not connected — start it as the driver's section in the reference describes under **Browser not running**, then re-check. Stop and ask the user to open it only when the driver has no way to start it, or it is still unreachable after starting.
5. **Clear the driver's setup gate** as its section in the reference describes.
6. **Find or open the Xiaohongshu tab.** List the tabs the driver can reach and read each `creator.xiaohongshu.com` tab with the Step 3 snippet:
   - **One or more XHS tabs:** with `--draft auto` or `current`, take the one whose stage is `editor`, `text` or `publish`; otherwise take any of them. Several on a note → ask which.
   - **No XHS tab** (the browser is open on other sites, or on none): open a new tab at `https://creator.xiaohongshu.com/publish/publish?from=menu&target=image`. Never navigate a tab that is showing another site. With `--draft current` there is no note to use: stop and say so.
   - **The user says the note is open in a tab the driver cannot reach** (some drivers only see the tabs they opened): with `--draft current`, ask the user to close that tab and rerun with `auto`. Otherwise open a new tab as above, and ask the user to close their tab first: two tabs autosaving the same draft overwrite each other.

If the page shows a login screen, stop and ask the user to log into Xiaohongshu in that browser, then re-check.

**Page JavaScript.** Every snippet is a self-contained arrow function invoked in place — `(async () => { … })()` — returning `JSON.stringify(...)` of its result, so it runs unchanged on every driver. A driver that returns the promise itself rather than its value (it comes back as `{}`) needs `await` in front of the snippet; `references/browser-drivers.md` names those drivers. No snippet returns `location.href`: some drivers withhold any result that carries a URL's query string.

### Step 3 — Read where the tab is

```js
(() => {
  const cards = document.querySelectorAll('.card-page').length;
  const images = document.querySelectorAll('.img-list .img-container img').length;
  const textTitle = document.querySelector('textarea[placeholder="输入标题"]');
  const textBody = document.querySelector('.tiptap.ProseMirror');
  const publishTitle = document.querySelector('input[placeholder*="标题"]');
  const stage = images ? 'publish' : cards ? 'editor' : (textTitle || textBody) ? 'text' : 'other';
  const title = stage === 'text' ? (textTitle ? textTitle.value : '')
    : publishTitle ? publishTitle.value : null;
  return JSON.stringify({
    path: location.pathname,
    stage,
    cards,
    images,
    title,
    bodyChars: textBody ? textBody.innerText.trim().length : null,
    login: /login/.test(location.pathname)
  });
})()
```

- `stage: editor` — the 一键排版 card editor is open with `cards` cards.
- `stage: text` — the 写长文 text editor is open: the note has not been laid out as cards, or the user went 返回 from the card editor. `title` and `bodyChars` say whether it holds anything.
- `stage: publish` — the publish page already holds `images` rendered images.
- `stage: other` — no note is open.

Then route by `--draft`:

- **`--draft auto`**: `editor` → Step 5; `text` → Step 5 (it starts with the text editor); `publish` → Step 6; `other` → Step 4. A `text` stage whose `title` is empty and `bodyChars` is 0 is a blank new note, not one to export: go to Step 4 instead.
- **`--draft current`**: `editor` → Step 5; `text` → Step 5; `publish` → Step 6; `other` → stop and tell the user no note is open in that tab. A blank `text` stage stops too: there is nothing to export.
- **`--draft <title>`**: always Step 4, unless the open note's `title` already matches it.

**If the stage is `publish` at this point, the user may have been working on that page.** Step 7 navigates the tab away, and whatever was typed there since the last 暂存离开 is lost. Say so and ask before continuing.

### Step 4 — Open the draft from 草稿箱

1. Navigate the tab to `https://creator.xiaohongshu.com/publish/publish?from=menu&target=image` unless it is already there.
2. Open the drafts drawer, read every tab's count, and list the 长文笔记 drafts — a 写长文 note is saved there; drafts in the other tabs are not 一键排版 notes and are never exported:

   ```js
   (async () => {
     const wait = ms => new Promise(r => setTimeout(r, ms));
     let button;
     for (let k = 0; k < 20 && !button; k++) {
       button = document.querySelector('.draft-title');          // 草稿箱(N)
       if (!button) await wait(500);
     }
     if (!button) return JSON.stringify({ error: '草稿箱 button not found' });
     button.click();
     await wait(1000);
     const tabs = [...document.querySelectorAll('.draft-tabs .tab-item')];
     const counts = Object.fromEntries(tabs.map(t => {
       const m = t.textContent.trim().match(/^(.+?)\((\d+)\)$/);
       return m ? [m[1], Number(m[2])] : [t.textContent.trim(), null];
     }));
     const drafts = [];
     const longform = tabs.find(t => t.textContent.includes('长文笔记'));
     if (longform && counts['长文笔记'] !== 0) {
       longform.click();
       await wait(1000);
       for (const item of document.querySelectorAll('.draft-list .draft-item')) {
         drafts.push({
           id: item.dataset.draftId,
           title: (item.querySelector('.draft-title-text') || {}).textContent || '',
           saved: (item.querySelector('.draft-time') || {}).textContent || ''
         });
       }
     }
     return JSON.stringify({ counts, drafts });
   })()
   ```

   `counts['长文笔记']` must equal the number of `drafts`; if it is larger, scroll the drawer's list to the bottom and read it again.

3. **Choose the draft** by how many 长文笔记 drafts there are:
   - **None:** stop. Tell the user this browser's 草稿箱 has no 长文笔记 drafts — give the other tabs' `counts` if any are non-zero, since those notes are not 一键排版 cards — and that drafts are kept per browser, so a note written in another browser has to be exported from that one.
   - **One:** with `auto`, take it. With a title, take it only if it matches.
   - **Several:** with a title, take the one that matches; with `auto`, or when more than one matches, list them with their `saved` time and ask which.

   Match a title ignoring line breaks and spaces. If nothing matches, stop and list the drafts there are.
4. **Open it** — click that item's **编辑**. Never click **删除**:

   ```js
   (async () => {
     const item = document.querySelector('.draft-item[data-draft-id="<draft id>"]');
     if (!item) return JSON.stringify({ error: 'draft not in the list' });
     const edit = [...item.querySelectorAll('.draft-actions .btn')].find(b => b.textContent.trim() === '编辑');
     edit.click();
     return JSON.stringify({ opened: '<draft id>' });
   })()
   ```

5. Poll the Step 3 snippet until the stage is `editor`, `text` or `publish` and the count stops changing, then continue at Step 5 (`editor` or `text`) or Step 6 (`publish`). A draft saved after 一键排版 opens in the card editor; one saved before it opens in the text editor.

### Step 5 — Click 下一步 so XHS renders the images

1. **If the stage is `text`, lay the note out as cards first.** Skip this substep when the stage is `editor`: the note already has its template, and nothing here changes it. With a blank note (`title` empty and `bodyChars` 0), stop: there is nothing to lay out. Otherwise, before clicking anything:

   1. **Decide who lays it out** by `--template`:
      - **`--template ask`**: ask the user whether the agent should apply a template, or they will lay the note out in the editor themselves. Agent → continue at 1.2. Themselves → 1.6.
      - **`--template agent`** or a template name → 1.2.
      - **`--template editor`** → 1.6.
   2. **Choose the template and background.**
      - **A template name was given** (by `--template` or in answer to 1.1): use it, with the background given or else its first swatch.
      - **`--template ask`**: show the user the template list from `references/templates.md` — each template's name, its backgrounds (colour word and hex) and its look — and ask for a template and a background, or for the agent to choose. A template named without a background gets its first swatch.
      - **`--template agent`**, or the user asked the agent to choose: read the copy, then pick the template whose **Suits** and **Look** in `references/templates.md` fit its subject and tone best, and the background that fits its mood. Say what you picked and why in one sentence.

        ```js
        (() => JSON.stringify({
          title: (document.querySelector('textarea[placeholder="输入标题"]') || {}).value || '',
          body: ((document.querySelector('.tiptap.ProseMirror') || {}).innerText || '').slice(0, 3000)
        }))()
        ```
   3. **Click 一键排版.** If the note was laid out before (the user went 返回 from the card editor), say that its earlier template is replaced. Tag the button, then real-click it — by `[data-xhs-export="layout"]` or the `XHS-EXPORT-LAYOUT` label:

      ```js
      (() => {
        const layout = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '一键排版');
        if (!layout) return JSON.stringify({ error: '一键排版 not found' });
        layout.setAttribute('data-xhs-export', 'layout');
        layout.setAttribute('aria-label', 'XHS-EXPORT-LAYOUT');
        return JSON.stringify({ tagged: true });
      })()
      ```

      Poll the Step 3 snippet until the stage is `editor`, then poll the live-list snippet in `references/templates.md` until it returns templates. If the chosen template or background is not on the live list, show the user the live list and ask again.
   4. **Select the template, then its background.** Tag the chosen template card and its background swatches:

      ```js
      (() => {
        document.querySelectorAll('[data-xhs-export="template"], [data-xhs-export^="background-"]').forEach(e => {
          e.removeAttribute('data-xhs-export');
          e.removeAttribute('aria-label');
        });
        const card = [...document.querySelectorAll('.template-list .template-card')]
          .find(c => c.querySelector('.template-title').textContent.trim() === '<template>');
        if (!card) return JSON.stringify({ error: 'template not found' });
        card.scrollIntoView({ block: 'center' });
        card.setAttribute('data-xhs-export', 'template');
        card.setAttribute('aria-label', 'XHS-EXPORT-TEMPLATE');
        const swatches = [...card.querySelectorAll('.color-item')];
        swatches.forEach((s, i) => {
          s.setAttribute('data-xhs-export', 'background-' + (i + 1));
          s.setAttribute('aria-label', 'XHS-EXPORT-BACKGROUND-' + (i + 1));
        });
        return JSON.stringify({
          selected: card.classList.contains('selected'),
          backgrounds: swatches.map(s => s.style.getPropertyValue('--item-color').trim().toUpperCase()),
          activeBackground: swatches.findIndex(s => s.classList.contains('active')) + 1
        });
      })()
      ```

      Real-click the template card (`XHS-EXPORT-TEMPLATE`) unless it is already `selected` — 一键排版 preselects the template used last, which may already be the chosen one — and wait a second for the cards to re-render. Run the tagging snippet again, since the panel re-renders, then real-click the chosen swatch (`XHS-EXPORT-BACKGROUND-<n>`, numbered from 1) unless it is already the active one. A newly selected template starts on swatch 1.
   5. **Verify** what the editor applied, and stop if either differs from the choice:

      ```js
      (() => {
        const card = document.querySelector('.template-list .template-card.selected');
        const active = card && card.querySelector('.color-item.active');
        return JSON.stringify({
          template: card ? card.querySelector('.template-title').textContent.trim() : null,
          background: active ? active.style.getPropertyValue('--item-color').trim().toUpperCase() : null,
          cards: document.querySelectorAll('.card-page').length
        });
      })()
      ```

      Tell the user the template, background and card count, then continue at substep 2.
   6. **The user lays it out.** Ask them to click 一键排版 and pick a template and background in the editor, and to say when they are done. Then poll the Step 3 snippet until the stage is `editor`, report the template and background with the 1.5 snippet, and continue at substep 2.
2. Record the card count from the editor's own page labels, and tag the 下一步 button. The button renders a moment after the cards, so the snippet waits for it:

   ```js
   (async () => {
     let next;
     for (let k = 0; k < 20 && !next; k++) {
       next = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '下一步');
       if (!next) await new Promise(r => setTimeout(r, 500));
     }
     const labels = [...document.querySelectorAll('.card-page')].map(e => e.textContent.trim());
     if (!next) return JSON.stringify({ error: '下一步 not found' });
     next.setAttribute('data-xhs-export', 'next');
     next.setAttribute('aria-label', 'XHS-EXPORT-NEXT');
     return JSON.stringify({ cards: labels.length, labels });
   })()
   ```

3. Click the tagged button with the driver's **real click** — by `[data-xhs-export="next"]` or by the `XHS-EXPORT-NEXT` label. Apart from 一键排版, the template and the background in substep 1, this is the only thing this skill clicks in the editors or on the publish page; never click 发布, 暂存离开 or 返回, and never change the template of a note that was already in the card editor.
4. Poll until the publish page holds one finished image per card:

   ```js
   (() => {
     const imgs = [...document.querySelectorAll('.img-list .img-container img')];
     return JSON.stringify({
       images: imgs.length,
       ready: imgs.filter(i => i.complete && i.naturalWidth > 0).length,
       sizes: [...new Set(imgs.map(i => i.naturalWidth + 'x' + i.naturalHeight))]
     });
   })()
   ```

   Carry on when `ready` equals the card count. If it stays below for 30 seconds, take a screenshot and report what the page shows.

### Step 6 — Start the receiver

Read the note's title from the publish page (the Step 3 snippet's `title`, or the draft's title from Step 4). Resolve `--output-dir`: the default is `~/Downloads/xhs-images/<title>/`, with line breaks, slashes and characters a file system refuses replaced by spaces and runs of spaces collapsed. State it.

Start the receiver **in the background** — it keeps running until the export arrives:

```bash
python3 <skill-dir>/scripts/script.py receive --output-dir "<output-dir>" --prefix "<prefix>"
```

Its first output line is `{"receiver_url": "...", "token": "..."}`. Read it before Step 7.

### Step 7 — Hand the images to the receiver

The publish page cannot send the images to this machine itself; it can only leave them in `window.name`, which the tab keeps when it navigates. This snippet packs every image, in card order, and then sends the tab to the receiver:

```js
(async () => {
  const imgs = [...document.querySelectorAll('.img-list .img-container img')];
  const toDataUrl = async src => {
    const blob = await (await fetch(src)).blob();
    return await new Promise(r => { const f = new FileReader(); f.onload = () => r(f.result); f.readAsDataURL(blob); });
  };
  const images = [];
  for (const img of imgs) images.push(await toDataUrl(img.src));
  window.name = JSON.stringify({ token: '<token>', title: '<title>', images });
  setTimeout(() => { location.href = '<receiver_url>'; }, 200);
  return JSON.stringify({ packed: images.length, chars: window.name.length });
})()
```

`packed` must equal the card count. The receiver page posts each image to the script, clears `window.name`, and changes its title to `XHS-EXPORT-DONE <n>` (or `XHS-EXPORT-ERROR`).

### Step 8 — Check what was saved

When the receiver exits, read its output — the manifest it also writes to `<output-dir>/manifest.json`:

- exit `0`: `saved` equals `expected`, and `missing` is empty;
- exit `1` with `missing`: some images did not arrive — rerun from Step 4;
- exit `1` with `error`: report it as given.

Then check, and report any difference:

1. `saved` equals the card count from Step 5 (or the image count from Step 3).
2. Every image has the same `width` × `height` as the `sizes` Step 5 read from the page.
3. Look at the first image (`<prefix>-1`) and confirm it is the note's cover card.

### Step 9 — Return the tab to Xiaohongshu

Navigate the tab back to `https://creator.xiaohongshu.com/publish/publish?from=menu&target=image`. The note itself is untouched and still in 草稿箱. Make sure the receiver process has exited; stop it if it has not.

## Output

```
<output-dir>/
├── <prefix>-1.jpg      # cover card
├── <prefix>-2.jpg
├── …
└── manifest.json       # title, expected, saved, missing, and per image: index, path, format, width, height, bytes
```

Report the folder, the number of images and their size, and that nothing was published.

## Gotchas

- XHS names nothing: the images exist only as `blob:` URLs on the publish page, and they are gone once the tab leaves it. Re-entering the publish page means opening the draft and clicking 下一步 again.
- 草稿箱 lives in that browser's local storage, not on the account. A draft made in one browser does not show up in another.
- The images are JPEG whatever the page calls them; the script names files by their real format.
- The card editor renders cards lazily: `.editor-item-new` can count fewer cards than the note has. Count by the `.card-page` labels (`1/8` … `8/8`).
- Opening a new blank 写长文 note and leaving it saves nothing to 草稿箱, so navigating away from a blank text editor is safe.
