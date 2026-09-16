# 知乎专栏文章编辑器（zhuanlan.zhihu.com/write）行为笔记

> 来源：对一次真实操作的 HAR 网络记录的分析。DOM 会变，下面记录的是**行为和接口**，
> 不是写死的选择器——运行时仍需通过当前的浏览器驱动现场定位元素（见 `browser-drivers.md`）。

## 编辑器基础

- 编辑器基于 **Draft.js**（`contenteditable`），不是 ProseMirror。
- 标题输入框：`textarea[placeholder*="请输入标题"]`（另见 skillhub 的
  `dom-selectors.md`）。**知乎不会从导入的正文自动提取标题**——`articles/drafts`
  和后续 `draft` PATCH 请求里都没有出现过服务端自动填充的 `title` 字段；标题必须
  在这个输入框里手动输入。

## 导入 Markdown（“从本地导入”一类的入口）

请求：`POST https://www.zhihu.com/api/v4/document/convert`
（`multipart/form-data`，字段：`document`（文件，`Content-Type: text/markdown`）、
`task_id`、`scene=article`、`content_token`）

- 触发方式：把本地 `.md` 文件设置到对应的隐藏 `<input type="file">`
  （用浏览器工具的文件上传能力，而不是点系统文件选择框）。
- 返回 `{"code":0,"data":{"html_content": "..."}}`，是转换后的 HTML，随后
  这段 HTML 会被塞进编辑器的 `contenteditable`。
- **markdown 里的图片语法会被知乎自动转换成
  `<img reupload src="{相对路径}/img-N.png" alt="img-N.png" />`**，随后编辑器
  会为每张图片再发一个
  `POST https://zhuanlan.zhihu.com/api/uploaded_images`（`multipart/form-data`，
  字段 `url` + `source=article`），尝试把这个相对路径当 URL 去抓取重新上传。
  **这一步在本地 markdown 场景下必然失败**（实测返回
  `400 {"error":{"message":"图片地址不合法","code":400,"name":"MalformRequestException"}}`），
  因为相对路径根本不是可访问的 URL。

  **公开可访问的 `https` 图片地址则能转存成功。** 实测把两张上传到图床 img.scdn.io 的 PNG
  （默认域名 `img.cdn1.vip`、大陆 ESA 域名 `esaimg.cdn1.vip` 各一张）写进 markdown 导入，
  几秒内两张都变成 `https://pic-private.zhihu.com/…`，位置和尺寸都正确，没有“上传失败”。
  那次网络记录没有抓到转存所走的请求，所以转存具体调用哪个接口未经确认。

  **所以本 skill 先把每张图上传到图床，把 markdown 里的图片换成图床地址再导入**，
  由导入流程自己转存；图床拒收的图片（如 HEIC、SVG）才换成纯文本占位符
  （`【ZHIHU-IMG-N】`），避免触发必然失败的本地路径转存，导入完成后再逐张手动插入。

- 转存后的图片块在编辑器顶层是 `<figure>`，前后各有一个空 `<div>`。
- 在页面 JS 里手工 `POST /api/uploaded_images`（`url` + `source=article`，带 `_xsrf`）
  会被网关在 100ms 内直接回 `403`，还没到抓图那一步——编辑器自己的请求带有裸 `fetch`
  没有的请求头。要转存，就走导入流程。

## 创建 / 保存草稿

- `POST https://zhuanlan.zhihu.com/api/articles/drafts`，body 是
  `{"content": "<导入后的 HTML>"}`，返回文章 `id`（草稿 ID）和
  `url`（形如 `https://zhuanlan.zhihu.com/p/<id>`，此时内容仍是草稿状态）。
- 之后编辑器每次变更（打字、插入图片等）会持续发
  `PATCH https://zhuanlan.zhihu.com/api/articles/<id>/draft`，body 同样是
  `{"content": ..., "table_of_contents": ..., "delta_time": ..., "can_reward": ...}`。
  这是知乎编辑器自带的自动保存，**不需要 skill 手动调用**——只要在浏览器里正常编辑，
  草稿会自动持续保存。

## 本地图片上传（完整链路）

插入一张本地图片时（粘贴、或走上传弹窗），前端依次发出：

1. `POST https://api.zhihu.com/images`，body `{"image_hash": "<内容 MD5>", "source":"article"}`，
   返回 `{"upload_token": {...}, "upload_vendor": "ali", "upload_file": {"image_id": "...",
   "state": 2, "object_key": "v2-<hash>"}}`。
2. `PUT https://zhihu-pics-upload.zhimg.com/v2-<hash>`，请求体就是图片二进制，
   `Content-Type: image/png`。**这一步才是真正的字节上传。**
3. `PUT https://api.zhihu.com/images/<image_id>/uploading_status`，body
   `{"upload_result":"success"}`。
4. 之后 `GET https://api.zhihu.com/images/<image_id>` 轮询到就绪，草稿 PATCH 里就
   出现真正的 `<img src="https://pic-private.zhihu.com/...">`。

若某张图的哈希此前已上传过，第 1 步会直接命中去重、跳过第 2 步。

**自动化如何触发这条链路**：走编辑器自己的 UI 就行，不需要剪贴板、也不需要合成事件。
点工具栏 图片 打开上传弹窗后，弹窗里会出现一个 `accept` 以
`image/webp,image/jpg,image/jpeg,image/png` 开头的 `<input type="file">`
（按 `accept` 前缀精确挑，别按描述找：附件那个 input 也收 `.png`/`.jpg`，
页面上还可能有一个 `accept` 就是 `image/*` 的 input，同样不是它）；用浏览器驱动的
上传动作把本地文件交给这个 input（**不要自己去点它**，点击会打开自动化无法填写的
系统原生文件框）。

**浏览器驱动的上传动作本身就会触发 input 的 change 事件**，
**不要再手动派发 `change`/`input` 事件**——处理器会跑两遍，图片被插入两次。

图片会插入到编辑器光标所在位置，但 `src` **不保证**立刻就是
`https://pic-private.zhihu.com/…`：实测出现过先是 `blob:` URL、插入后才继续上传的情况，
也出现过直接变成“上传失败”。所以要轮询 `src` 直到变成 `pic…`，
失败时点该块上的「重试」按钮，它能原地把这张图重传好。

**判断插入是否完成，要数编辑器里的 `img` 数量是否加一**，不要等某段文案或某个按钮。
两种情况都实测出现过：写入文件后图片直接落到光标处，弹窗回到「本地图片上传」初始页，
底部既没有「已上传 N 张图片」也没有「插入图片」；也有弹窗停在「已上传 N 张图片」、
要点「插入图片」才插入的情况，这时直接关掉弹窗会把这次上传丢掉，也不报错。
所以数量没变、而「插入图片」按钮在，就点它。

**选中占位符用键盘**：单击置入光标，再 `End`、`Shift+Home` 选中整行。三击只在浏览器
窗口处于前台时才会选中（自动化操作时它常常不在前台），而且选区可能连行尾换行一起选中
（`getSelection()` 读到 `【ZHIHU-IMG-N】\n`），这时按 Backspace 会删掉整段，光标落到
相邻段落里，而不是留在一个空段落中。插入前要确认两个邻居之间确实有一个空块、
且光标就在里面；否则点进后一段的第一行，
按 Home、Enter 把它往下挤，再按 ArrowUp 进入新建的空段落。不要在前一段按 End 再按 Enter：
`End` 到的是可视行尾而不是块尾，段落一换行就会从中间劈开。

## 已知限制 / 排错提示

- 若 `document/convert` 或 `articles/drafts` 返回非 200 / `code` 非 0，多半是没登录
  或触发了风控——按 SKILL.md 的登录检查步骤处理，不要重试脚本层面的接口调用。
- **一次只插一张图。** 如果绕开弹窗、让图片在编辑器内部边插边传（例如合成 paste
  事件），并发插入会让上传卡死：卡住的块先显示“图片上传中”，随后变成“上传失败”，
  又会让整篇草稿的自动保存一直停在“草稿保存中”。走弹窗流程能大幅降低这个概率，
  但并不能完全避免——实测走弹窗也遇到过单张“上传失败”。
- **图片块是 atomic block，Backspace/Delete 删不掉它，但 UI 能删。**
  鼠标悬停在图片上会出现「×」删除控件，插重了就用它删掉多余的那个；
  显示“上传失败”的块上有「重试」按钮，点一下就能原地重传成功。
  这两个入口都比重建整篇草稿便宜，位置错了才需要重建。
- **DOM 里看到的内容不等于服务端已保存的内容。** 用
  `GET /api/articles/<id>/draft` 校验真正落库的 `content`；自动保存滞后时，
  强制跳转一次同一个编辑页（会弹 “Leave site?”）可以把待保存内容冲刷出去。
- **工具栏按钮按 `aria-label` 找，不要按文字找。** 按钮的文字写在 `aria-label` 里
  （`button[aria-label="图片"]`、`button[aria-label="导入"]`）；它们的 `innerText` 前面
  带一个零宽空格和换行（`"​\n图片"`），`trim()` 去不掉零宽空格，按文字精确匹配会找不到。
- **弹窗没关干净会把后续点击全吃掉。** 上一张图留下的弹窗还在时，后面的点击都落在
  弹窗上，表现出来却是「选区是空的」，看着像选择器失效。每插一张图之前先查一次
  `document.querySelector('.Modal')`，有就按 Escape，按完再查，一次不一定关得掉。
- Draft.js 只认真实输入产生的选区：用 `Range` + `Selection` 程序化设置的选区，
  编辑器不会同步，随后的按键会作用在别处。选中占位符用「单击 + `End` + `Shift+Home`」。
- 刚加载完的 `/edit` 页可能已经渲染出正文、但还没接管键盘输入；此时打字没反应
  不代表编辑器只读，等它初始化完（标题栏变成“写文章 - 知乎”）再操作。
- 标签页在后台时可能被浏览器挂起：页面看起来正常，但所有脚本调用都会超时。把标签页切到前台
  再试；页面还没初始化完（标题不是“写文章 - 知乎”）时不要点击任何东西。
- **页面隐藏久了，保存可能被压住。** `document.visibilityState` 为 `hidden`（标签页切到后台，
  或窗口被别的窗口挡住）超过几秒后，浏览器会大幅节流页面的定时器。实测：隐藏 35 秒后插入的图片
  上传、处理都成功（请求全是 200），但之后 65 秒里没有发出 `PATCH …/draft`，状态停在“草稿保存中”；
  页面一回到前台，几秒内就补发保存。隐藏前就排上的保存（刚隐藏就打字、隐藏 3 秒左右图片处理完）
  仍会照常发出。网络故障的表现不同：保存请求会发出然后失败。服务端草稿落后时先查可见性，
  不要急着刷新页面。
- **「上传失败」不一定是真失败。** 实测前台状态下，编辑器轮询 `GET api.zhihu.com/images/<id>`
  约 8 次后放弃，块上显示“上传失败”，而稍后该接口返回 `"status": "success"`——是知乎服务端处理慢，
  编辑器先不等了。遇到时点「重试」。
- 发布按钮（文字含“发布”）本 skill **绝不点击**——只做到草稿保存为止。
