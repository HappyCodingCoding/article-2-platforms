---
name: qingyun-xhs-image-export
description: >-
  Exports the card images Xiaohongshu (小红书 / Rednote) renders from a 写长文 (long-form) note’s 一键排版 card layout to a local folder, in the user's own logged-in browser, driven through whatever browser control the current agent has — its own browser extension or built-in browser (Claude in Chrome, the Claude desktop app's browser pane, Codex's Chrome plugin) or the agent-neutral `bsk` CLI. Opens the draft from 草稿箱 (or picks up the editor or publish page already open), clicks 下一步 so XHS renders the final images, then carries them out of the page into a folder through a local receiver run by its script. A note not yet laid out gets a template first: the agent applies the 一键排版 template and background the user picks from the list, or the one that suits the copy, or the user lays it out in the editor (`--template`). With no 长文笔记 draft, it imports a .docx/.doc/.md/.txt file into a new note through the editor's 从文件导入 (`--import`, or a path it asks for), or opens a blank note for the user to import or write themselves. Before 一键排版 and before 下一步 it asks whether the user wants to edit the note first (`--review`). `--draft` picks the draft by title, `--output-dir` and `--prefix` set where and how the files are saved, `--aspects` saves XHS's own 3:5 cards, side-padded 3:4 copies, or both (default), `--driver` forces a browser driver. Never publishes, never deletes a draft. Triggers on "下载小红书配图", "导出小红书图片", "save the XHS card images", "download the images the XHS editor made", "xhs-image-export", or a request to get the 一键排版 card images out of the Xiaohongshu editor.
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
| `--review` | option | `ask` / `no` | `ask` | `ask` asks, right before the agent clicks 一键排版 (Step 5.1.3) and again right before 下一步 (Step 5.2), whether the user wants to edit the note's contents in the 长文 draft first, and waits while they do. `no` renders straight away, for unattended runs. Not asked when the run starts on a publish page that already holds images. |
| `--aspects` | option | `3:5` / `3:4` / `3:5,3:4` | `3:5,3:4` | Which aspect ratios to save. `3:5` is XHS's own card ratio (1440×2400), saved exactly as rendered. `3:4` pads each card at the left and right with its own background colour (1800×2400): nothing is cut off, but the card fills 80% of the width, so its text shows smaller. `3:5,3:4` saves both. |
| `--import` | option | path to a local `.docx`, `.doc`, `.md`, `.markdown` or `.txt` file | — | A document to turn into a new 长文 note when 草稿箱 has no 长文笔记 drafts (Step 4.6), through the editor's own 从文件导入. Infer it from any document path the user gives. Without it, a run that finds no drafts asks for a document, or for the user to import or write the note themselves (Step 4.3). When drafts do exist, ask whether to import it as a new note or export an existing draft. |
| `--driver` | option | `auto` / `claude-in-chrome` / `claude-browser-pane` / `codex-chrome` / `bsk` | `auto` | How Step 2 reaches the browser. `auto` takes the running agent's first usable driver from `references/browser-drivers.md`. A named driver is for a user who prefers one; the run stops if it is unavailable. |

## Workflow

### Step 1 — Resolve the options

State `--draft`, `--template`, `--review`, `--prefix`, `--aspects` and `--driver` as resolved. Any aspect other than `3:5` and `3:4` is not supported: say so and ask, rather than dropping it. When `--template` names a template, check it, and its background if given, against `references/templates.md` now; if either is not there, show the matching row or the list and ask, before touching the browser. `--output-dir` is stated in Step 6, once the note title is known; when the user named a folder, state it now.

### Step 2 — Choose the browser driver, then open Xiaohongshu

Every browser action from here to Step 9 goes through one driver. Choose it as `references/browser-drivers.md` describes, then use only that driver for the rest of the run.

1. **Identify the agent you are running in** and say which it is.
2. **Pick the driver.** With `--driver auto`, inventory the agent's own browser capabilities first and use one that passes the checklist below; fall back to `bsk` only when the agent has none. With a named `--driver`, use that one and stop if it is unavailable. State the chosen driver.
3. **Check the driver can do everything this skill needs.** It must be able to:
   - open or reuse a tab in a browser where the user is logged into Xiaohongshu, and navigate that tab to a URL;
   - run JavaScript in the page and return its value, awaiting a promise;
   - click an element with real input;
   - take a screenshot;
   - for an import (Step 4.6) only: put a local file into a page `<input type="file">` without opening a native file picker. A driver without it can still run everything else; Step 4.3 then offers the user to import the document themselves.

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
   - **None:** close the drawer. With `--import`, import that document as a new note — Step 4.6. Without it, do not stop: tell the user this browser's 草稿箱 has no 长文笔记 drafts — give the other tabs' `counts` if any are non-zero, since those notes are not 一键排版 cards, and say that drafts are kept per browser, so a note written in another browser has to be exported from that one — then ask how to get a note:
     - **Give a document to import** — the user replies with a path to a `.docx`, `.doc`, `.md`, `.markdown` or `.txt` file. Treat it as `--import` and go to Step 4.6. If the driver cannot upload files (Step 2.3), say so and offer the next answer instead.
     - **Import or write it themselves** — open a blank 写长文 note for them as Step 4.6.2 does, and tell them they can use the toolbar's 从文件导入 (its last button) or type or paste the text, then say when the note is ready. When they do, poll the Step 3 snippet until the stage is `text` with a non-empty `title` or `bodyChars` above 0 — if the title is empty, offer to fill it as Step 4.6.5 does — wait for the autosave as Step 4.6.6 does, and continue at Step 5. If they lay it out with 一键排版 themselves and the stage is already `editor`, continue at Step 5 all the same: its substep 1 is skipped.
     - **Stop** — end the run with nothing exported.
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
6. **Import a document as a new note** — only from substep 3's **None** branch (with `--import` or a document the user gave there), or when the user chose to import although drafts exist.
   1. **Check the file.** It must exist and end in `.docx`, `.doc`, `.md`, `.markdown` or `.txt` — the formats 从文件导入 accepts; otherwise stop and say so. Use its absolute path.
   2. **Open a blank 写长文 note.** Navigate to `https://creator.xiaohongshu.com/publish/publish?from=menu&target=article`, find the **新的创作** button and real-click it, then poll the Step 3 snippet until the stage is `text` with an empty `title` and `bodyChars` 0. The import overwrites whatever the note holds, so it only ever goes into a blank one.
   3. **Open 从文件导入 and capture its file input.** The toolbar buttons carry no text, so find this one by its tooltip. Its upload area creates a file input only when clicked and opens a native picker with it; this snippet intercepts that, so no picker opens, and puts the input in the page, tagged, for the driver's upload action:

      ```js
      (async () => {
        const wait = ms => new Promise(r => setTimeout(r, ms));
        const tipOf = async b => {
          b.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
          await wait(250);
          const tips = [...document.querySelectorAll('.menu-tooltip, .d-popover-tooltip')].map(t => t.innerText.trim());
          b.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
          return tips[tips.length - 1] || '';
        };
        let importButton;
        for (const b of document.querySelectorAll('.menu-items-container button.menu-item')) {
          if ((await tipOf(b)) === '从文件导入') { importButton = b; break; }
        }
        if (!importButton) return JSON.stringify({ error: '从文件导入 not found' });
        importButton.click();
        let area;
        for (let k = 0; k < 10 && !area; k++) { await wait(300); area = document.querySelector('.import-from-file-modal .upload-area'); }
        if (!area) return JSON.stringify({ error: 'import dialog did not open' });
        const nativeClick = HTMLInputElement.prototype.click;
        const captured = [];
        HTMLInputElement.prototype.click = function () {
          if (this.type === 'file') { captured.push(this); return; }
          return nativeClick.call(this);
        };
        try { area.click(); await wait(500); } finally { HTMLInputElement.prototype.click = nativeClick; }
        const input = captured[0];
        if (!input) return JSON.stringify({ error: 'no file input was created' });
        if (!document.contains(input)) document.body.appendChild(input);
        input.setAttribute('data-xhs-export', 'import');
        input.setAttribute('aria-label', 'XHS-EXPORT-IMPORT-INPUT');
        input.style.cssText = 'position:fixed;left:10px;top:10px;width:220px;height:36px;opacity:1;z-index:99999;display:block;visibility:visible';
        return JSON.stringify({ accept: input.accept });
      })()
      ```

      `accept` must read `.docx,.doc,.md,.markdown,.txt`. **Never click the input or the upload area with the driver** — that opens a native file picker automation cannot fill.
   4. **Upload the file** into the tagged input with the driver's upload action — by `[data-xhs-export="import"]` or the `XHS-EXPORT-IMPORT-INPUT` label. The dialog closes by itself; poll the Step 3 snippet until `bodyChars` is above 0.
   5. **Set the title.** 从文件导入 fills only the body: the document's own title arrives as its first paragraph, and the title field stays empty. Read the first block:

      ```js
      (() => {
        const first = document.querySelector('.tiptap.ProseMirror > *');
        return JSON.stringify({ tag: first ? first.tagName : null, text: first ? first.innerText.trim() : '' });
      })()
      ```

      Treat it as the title when it is a heading (`H1`–`H3`), or a single line of at most 64 characters that does not end in 。！？ or another sentence ending. Otherwise ask the user for a title and leave the body as it is. To lift it, this snippet empties that block and joins it away. The block that moves up inherits the removed block's type, so a paragraph following an `H1` becomes an `H1`; the snippet then toggles that heading off with the toolbar's 一级标题 / 二级标题 button. Finally it fills the title field, which is a Vue-controlled textarea, so it goes through the native setter and an `input` event:

      ```js
      (async () => {
        const wait = ms => new Promise(r => setTimeout(r, ms));
        const body = document.querySelector('.tiptap.ProseMirror');
        const first = body.firstElementChild, second = first.nextElementSibling;
        const title = first.innerText.trim(), secondTag = second ? second.tagName : null;
        const select = (node, start, end) => {
          const range = document.createRange();
          range.setStart(node, start);
          range.setEnd(node, end);
          const selection = getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
        };
        if (second) {
          body.focus();
          select(first, 0, first.childNodes.length);
          document.execCommand('delete');
          await wait(200);
          const emptied = body.firstElementChild;
          if (emptied.innerText.trim() === '' && emptied.nextElementSibling) {
            select(emptied.nextElementSibling, 0, 0);
            document.execCommand('delete');
            await wait(200);
          }
          const lead = body.firstElementChild;
          const toggles = { H1: '一级标题', H2: '二级标题' };
          if (lead.tagName !== secondTag && toggles[lead.tagName]) {
            select(lead, 0, 0);
            for (const b of document.querySelectorAll('.menu-items-container button.menu-item')) {
              b.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
              await wait(250);
              const tips = [...document.querySelectorAll('.menu-tooltip, .d-popover-tooltip')].map(t => t.innerText.trim());
              b.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
              if (tips[tips.length - 1] === toggles[lead.tagName]) { b.click(); break; }
            }
            await wait(300);
          }
        }
        const ta = document.querySelector('textarea[placeholder="输入标题"]');
        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, title.slice(0, ta.maxLength || 64));
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        await wait(500);
        const lead = body.firstElementChild;
        return JSON.stringify({
          title: ta.value,
          expectedTag: secondTag,
          firstTag: lead ? lead.tagName : null,
          firstBlock: lead ? lead.innerText.trim().slice(0, 40) : ''
        });
      })()
      ```

      Check that `title` is the lifted line, that `firstBlock` is the document's next block, and that `firstTag` equals `expectedTag`. If the tags differ, the moved-up block kept the wrong type: tell the user which block it is, so they can fix it in the editor. A title the user gave goes into the field the same way, without lifting anything.
   6. **Wait for the autosave** — poll until `.auto-save-time` shows a time, and note it changes after the title is set — then continue at Step 5: the note is now a `text` stage, and Step 5.1 lays it out.

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
   3. **Click 一键排版.** First, with `--review ask`, ask the user whether they want to change the note's contents in the 长文 text editor before it is laid out as cards — 一键排版 paginates the text exactly as it is now. If they do, tell them which browser and tab the note is open in, ask them to say when they are done, and do not touch the page meanwhile. Then poll the Step 3 snippet: `text` with a non-empty `title` or `bodyChars` above 0 → carry on here; `editor` → they laid it out themselves, so report the template, background and card count with the 1.5 snippet and continue at substep 2; `publish` → go to Step 6. Skip the question with `--review no`.

      If the note was laid out before (the user went 返回 from the card editor), say that its earlier template is replaced. Tag the button, then real-click it — by `[data-xhs-export="layout"]` or the `XHS-EXPORT-LAYOUT` label:

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
2. **Offer a last edit before rendering.** With `--review ask`, ask the user whether they want to change the note's contents in the 长文 draft before XHS renders the images — 下一步 renders the cards exactly as they are now. Skip this with `--review no`.
   - **No changes** → substep 3.
   - **They want to edit** → tell them which browser and tab the note is open in, and that they can edit the text directly on the cards in the card editor, or go 返回 to the text editor — warning that coming back with 一键排版 may replace the template — and ask them to say when they are done. Do not touch the page meanwhile. Then poll the Step 3 snippet: `editor` → report the template, background and card count with the Step 5.1.5 snippet, and go to substep 3; `text` → go back to substep 1, which lays the note out again; `publish` → they clicked 下一步 themselves, so go to Step 6.
3. Record the card count from the editor's own page labels, and tag the 下一步 button. The button renders a moment after the cards, so the snippet waits for it:

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

4. Click the tagged button with the driver's **real click** — by `[data-xhs-export="next"]` or by the `XHS-EXPORT-NEXT` label. Apart from 一键排版, the template and the background in substep 1, this is the only thing this skill clicks in the editors or on the publish page; never click 发布, 暂存离开 or 返回, and never change the template of a note that was already in the card editor.
5. Poll until the publish page holds one finished image per card:

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
python3 <skill-dir>/scripts/script.py receive --output-dir "<output-dir>" --prefix "<prefix>" --aspects "<aspects>"
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

1. `saved` equals the card count from Step 5 (or the image count from Step 3), and `images` holds one entry per card for each of `aspects`.
2. Every `3:5` image has the same `width` × `height` as the `sizes` Step 5 read from the page; every `3:4` image has the same height and a width of height × 3 ÷ 4.
3. Look at the first image of each aspect (`<prefix>-1`) and confirm it is the note's cover card; for `3:4`, also that the side bands match the card's background.

### Step 9 — Return the tab to Xiaohongshu

Navigate the tab back to `https://creator.xiaohongshu.com/publish/publish?from=menu&target=image`. The note itself is untouched and still in 草稿箱. Make sure the receiver process has exited; stop it if it has not.

## Output

```
<output-dir>/
├── <prefix>-1.jpg      # 3:5, as XHS rendered it — cover card
├── <prefix>-2.jpg
├── …
├── 3x4/                # 3:4, padded at the sides
│   ├── <prefix>-1.jpg
│   └── …
└── manifest.json       # title, aspects, expected, saved, missing, and per image: index, aspect, path, format, width, height, bytes
```

Only the folders for the aspects in `--aspects` are written: with `3:4` alone, the card files sit only in `3x4/`.

Report the folder, the number of cards, each aspect's size, and that nothing was published.

## Gotchas

- XHS names nothing: the images exist only as `blob:` URLs on the publish page, and they are gone once the tab leaves it. Re-entering the publish page means opening the draft and clicking 下一步 again.
- 草稿箱 lives in that browser's local storage, not on the account. A draft made in one browser does not show up in another.
- The images are JPEG whatever the page calls them; the script names files by their real format.
- The card editor renders cards lazily: `.editor-item-new` can count fewer cards than the note has. Count by the `.card-page` labels (`1/8` … `8/8`).
- Opening a new blank 写长文 note and leaving it saves nothing to 草稿箱, so navigating away from a blank text editor is safe.
- Leaving a 写长文 editor that holds content raises a "Leave site?" dialog, even after an autosave. When a step has to navigate away from one, use the driver's force option if it has one; a note already autosaved loses nothing.
