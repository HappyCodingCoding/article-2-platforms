# 知乎专栏文章编辑器（zhuanlan.zhihu.com/write）行为笔记

> 来源：对一次真实操作的 HAR 网络记录的分析。DOM 会变，下面记录的是**行为和接口**，
> 不是写死的选择器——运行时仍需用 `find` / `read_page` 现场定位元素。

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

  **这正是本 skill 自己先把图片替换成占位符（`【ZHIHU-IMG-N】`）再导入的原因**
  ——占位符是纯文本，不会触发这个必然失败的自动重传流程；图片改为在导入完成后，
  逐张手动插入。

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
点工具栏 图片 打开上传弹窗后，弹窗里会出现一个 `accept="image/*"` 的
`<input type="file">`；用浏览器工具把本地文件写进这个 input（**不要去点它**，
点击会打开自动化无法填写的系统原生文件框），弹窗底部出现「已上传 N 张图片」后，
再点「插入图片」，图片就会插入到编辑器光标所在位置，且 `src` 已经是
`https://pic-private.zhihu.com/…`（上传在点“插入图片”之前就完成了）。

**「上传」和「插入」是两件事**：选中文件只完成上传，不点「插入图片」就直接关掉弹窗，
这次上传会被丢弃，编辑器里什么都不会出现，也不会报错。

## 已知限制 / 排错提示

- 若 `document/convert` 或 `articles/drafts` 返回非 200 / `code` 非 0，多半是没登录
  或触发了风控——按 SKILL.md 的登录检查步骤处理，不要重试脚本层面的接口调用。
- **一次只插一张图。** 如果绕开弹窗、让图片在编辑器内部边插边传（例如合成 paste
  事件），并发插入会让上传卡死：卡住的块先显示“图片上传中”，随后变成“上传失败”，
  它既删不掉（Backspace/Delete 对这种 atomic block 无效），又会让整篇草稿的
  自动保存一直停在“草稿保存中”。走弹窗流程不会有这个问题，因为插入时上传已完成。
- **DOM 里看到的内容不等于服务端已保存的内容。** 用
  `GET /api/articles/<id>/draft` 校验真正落库的 `content`；自动保存滞后时，
  强制跳转一次同一个编辑页（会弹 “Leave site?”）可以把待保存内容冲刷出去。
- Draft.js 只认真实输入产生的选区：用 `Range` + `Selection` 程序化设置的选区，
  编辑器不会同步，随后的按键会作用在别处。选中占位符要用三击。
- 刚加载完的 `/edit` 页可能已经渲染出正文、但还没接管键盘输入；此时打字没反应
  不代表编辑器只读，等它初始化完（标题栏变成“写文章 - 知乎”）再操作。
- 发布按钮（文字含“发布”）本 skill **绝不点击**——只做到草稿保存为止。
