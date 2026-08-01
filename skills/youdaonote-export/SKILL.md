---
name: youdaonote-export
description: 有道云笔记一键导出/备份/迁移为本地 Markdown。用 when 用户需要导出有道云笔记、迁移到其他平台（飞书/Obsidian/语雀等）、或备份全部笔记。
category: productivity
author: dirtydamn
---

# 有道云笔记一键导出（自包含技能）

将有道云笔记**全部笔记**（含目录结构、图片、附件）导出为本地 Markdown。
技能内已内置开源项目 `youdaonote-pull`（作者 DeppWang，MIT License），**无需联网拉取任何代码**，开箱即用。

## 原理（30 秒版）

有道云笔记没有官方批量导出。本技能模拟 Web 端行为，调用有道私有接口 `note.youdao.com/yws/api/personal/...`：

| 接口 | 作用 |
|---|---|
| `getByPath` | 获取根目录 ID |
| `listPageByParentId` | 按目录列出文件（含子目录树） |
| `download` | 按 fileId 下载笔记内容（`convert=true` 服务端返回原始 XML/JSON） |

下载后用内置转换器把 XML/JSON 转成 Markdown，图片/附件链接改写为本地相对路径。

## 快速开始

```bash
# 1. 环境
cd scripts/youdaonote-pull
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # 或新版: requests markdownify Brotli win32-setctime

# 2. 填 Cookie（见下文三种方式）
# 3. 填 config.json（导出目录）
# 4. 运行
.venv/bin/python pull.py
```

## 获取 Cookie 的三种方式（任选其一）

### 方式 A：浏览器手动复制（最通用，任何平台）

1. 浏览器登录 [note.youdao.com/web/](https://note.youdao.com/web/)（**用账号密码登录**）
2. F12 → Network → 刷新 → 点任意请求 → 复制 Request Headers 的 Cookie 整行
3. 提取 `YNOTE_CSTK`、`YNOTE_LOGIN`、`YNOTE_SESS` 三个值填入 `cookies.json`

### 方式 B：扫码登录自动获取（推荐，无需已有登录态）

全程命令行，不依赖浏览器，任何平台可脚本化：

```bash
# 1. 生成二维码（有效期约 60 秒）
curl -s -c jar.txt "https://note.youdao.com/login/acc/qrcode/gen"
# → ynote://login/qr_verify?code=xxxxxxxx   ← 拿 CODE

# 2. 把 "ynote://login/qr_verify?code=CODE" 生成二维码图片（任意二维码库）
#    发给用户用「有道云笔记 App」扫码并在手机上确认

# 3. 轮询扫码状态（建议 2 秒一次）
curl -s -b jar.txt -c jar.txt "https://note.youdao.com/login/acc/qrcode/query?code=CODE"
# → {"status":"INIT"} / {"status":"CONFIRM","uid":"..."}

# 4. CONFIRM 后立即调用登录接口换取会话（关键！）
curl -s -b jar.txt -c jar.txt -X POST "https://note.youdao.com/login/acc/login" \
  -d "app=web&acc=qrcode&tp=tpac&product=YNOTE&qr_code=CODE&cf=7&systemName=Windows&deviceType=WindowsPC&timestamp=$(date +%s000)"

# 5. 查看 jar.txt，此时已有 YNOTE_LOGIN / YNOTE_SESS / YNOTE_PERS
```

> ⚠️ **核心发现**：`YNOTE_CSTK` 不会被扫码登录种下，但服务端**只校验格式不校验绑定**——随便填 8 位字母数字即可（如 `abc12345`）。这是整个流程能跑通的关键。

### 方式 C：macOS Safari 自动化（本机 Safari 已登录时）

```bash
# 读取非 HttpOnly cookie（YNOTE_CSTK / YNOTE_LOGIN）
osascript -e 'tell application "Safari" to tell front window to return (do JavaScript "document.cookie")'

# YNOTE_SESS 是 HttpOnly，JS 读不到；且 TCC 权限会挡住读取
# ~/Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies
# 最简单：直接用方式 B 扫码，或让用户重新密码登录后手动复制
```

## 配置说明

`config.json`：

```json
{
    "local_dir": "/绝对/路径/导出目录",   // 留空则导出到脚本目录下 youdaonote/
    "ydnote_dir": "",                    // 只导出指定顶层目录名，留空=全部
    "smms_secret_token": "",             // 留空=图片下载到本地；填 SM.MS token=图片传图床
    "is_relative_path": true             // 图片链接用相对路径（Obsidian 友好）
}
```

`cookies.json` 格式（列表内每项依次为 name/value/domain/path）：

```json
{
    "cookies": [
        ["YNOTE_CSTK", "8位任意字符", ".note.youdao.com", "/"],
        ["YNOTE_LOGIN", "登录cookie", ".note.youdao.com", "/"],
        ["YNOTE_SESS", "会话cookie", ".note.youdao.com", "/"]
    ]
}
```

## 输出

- 目录结构 = 有道云笔记目录树，逐层建文件夹
- 笔记 → `.md`（XML 老格式、JSON 新格式自动转换）
- 图片 → 每篇笔记旁 `images/` 子目录，链接改本地相对路径
- 附件/非文本（sql、drawio、xlsx、pdf、xmind 等）→ 原样字节保存
- 增量同步：重跑会跳过未变更文件（按修改时间对比）

## 常见问题与坑

1. **登录被踢**：新登录（任何方式）会踢掉旧会话。多端同时导出前先确认。
2. **二维码 60 秒过期**（`ecode:2600`）：过期重新 gen 即可，轮询脚本要能自动续码。
3. **`AUTHENTICATION_FAILURE (207)`**：Cookie 无效或 SESS 缺失，重新获取。
4. **`ecode 2300`**：CSTK 缺失或格式不对——确认填了 8 位字符。
5. **单目录 >1000 个文件会截断**：接口 `len=1000` 上限，超大目录需手动分批（ydnote_dir 指定子目录）。
6. **思维导图（xmind）和有道私有表格（lxtable）不转 Markdown**：原样保留，需从有道客户端单独导出图片兜底。
7. **Mac 必装 Brotli**：有道 note 内容用 br 压缩，缺了会转换失败。
8. **2017 年前的老笔记**是 HTML 格式，转换器有兜底逻辑但样式可能丢失。
9. **发布/开源前务必检查**：`cookies.json` 可能含真实 Cookie、`logs/` 含运行记录——清空或重置后再提交。

## 授权与致谢

内置工具：github.com/DeppWang/youdaonote-pull（MIT License，作者 Depp Wang）。
本技能封装的扫码登录流程与 CSTK 发现来自实际迁移实战（2026-08）。
