---
name: push-ledger
description: 基于飞书表格的「推送台账」——记录推过什么、查重、识别可补充的后续进展并自动归档。用 when 用户要按日/按班次推送内容、要台账式记录已推送内容、或要避免重复推送同一事件；新闻简报、行业简报、竞品动态、政策变化等各类自定义通知监测场景。
category: productivity
author: dirtydamn
---

# 推送台账

给「按日/按班次往外推送内容」这类工作流做记账：**每条推出去的内容都写进一张飞书电子表格**，下一批推送前先查历史，避免重复推、并识别「这条事件上次推过、现在有新进展 → 应该做补充」。

## 适用场景

- 新闻摘要、行业简报、竞品动态社群日报、运营通知，以及政策变化、公告发布、价格调整等**自定义通知监测**
- 每日/每班次给用户推送内容，需要「推过什么」的长期记忆
- 同一事件会持续发酵（如公司 IPO、事故调查、政策推进），需要区分「新事件」和「进展补充」
- 不希望台账无限膨胀，需要按阈值把老记录归档到历史工作表

## 前置条件

**① 必须装好 Lark CLI**，先自检：

```bash
command -v lark-cli        # 没输出 = 没装
lark-cli auth status       # 看身份是否 ready
```

**所有表格操作都用 `lark-cli` 完成**，没装就先根据这个文档装上：
  - Lark CLI：https://github.com/larksuite/cli

**② 必须拿到电子表格的读写权限**

- scope：读写用 `sheets:spreadsheet`（只读用 `sheets:spreadsheet:read`）

**③ 拿到台账地址**：电子表格 URL（`https://<租户>.feishu.cn/sheets/<token>`）。后面所有命令都用 `--url` 直接传它。

## 台账表结构

自建一张电子表格，7 列（两张工作表：`当前` + 归档用）：

| 字段 | 说明 |
|---|---|
| 日期 | `YYYY-MM-DD`（推送当日；跨零点时与用户确认按「推送日」还是「内容发生日」） |
| 类型 | 推送批次类型，**由用户定义、每次推送前询问用户**（如 `早报` / `晚报` / `突发`） |
| 题材类别 | **单值**，取自 [references/iptc-topics.md](references/iptc-topics.md) 的题材类别表 |
| 新闻类别标签 | **多值**，中文分号 `；` 分隔；**用户指定了领域时，此项直接填用户指定的领域**（详见下节） |
| 内容 | **≤100 字的一句话事实**；未特别指定时不展开 |
| 详细内容 | **默认留空**；仅当用户点名某类题材必须给详情时才填 |
| 来源 | 多个 URL，按 `1.` `2.` 编号，**每个 URL 之间用换行符分隔**（单元格内换行） |

**列顺序自定，按表头认列**：动手前先 `+csv-get` 读第 1 行确认列位，再决定写哪几列。本文档示例表把「来源」放在最后一列，也有表把「来源」放在「详细内容」前面——**别写死列号**。

**想省事可以直接复制一份现成模板**（可选，不是必须）：

- 模板表：https://nothing-plat.feishu.cn/sheets/B51ysqyQ4hFkRxtKamhcE6Ern2c
- 在飞书里打开 → 右上角「…」→ **创建副本**（复制到你自己的空间），再把副本的 token 当台账地址用
- 自己按上表建 7 列同样可以，格式是一样的

工作表命名：

- `当前`：正在累积的台账（阈值见「归档」）
- `归档-YYYY-MM-DD`：归档后的历史表

## 字段规则（重点）

### 新闻类别标签 的取值逻辑

按下面的顺序判断，命中即停：

1. **用户指定了领域**（如「今天的 AI 动态」「财经领域要闻」）→ 这一列**统一填用户指定的那个领域**（`AI领域`、`财经` …），不要再去填 IPTC 细分类别。
2. 用户没指定领域 → 填**一个或多个 IPTC 题材类别**，中文分号分隔，如 `科学技术；政治`。
3. `题材类别` 列**始终**填 [references/iptc-topics.md](references/iptc-topics.md) 里的单值类别，不受上面两条影响。

### 内容

- **一句话事实**，≤100 字；写「谁做了什么、结果如何」，不写评论、不写"引发广泛关注"这类空话
- 事实里的数字、机构名、时间要能在来源里核到
- 用户没要求详细内容 → `详细内容` 留空，不要把细节塞进 `内容`

### 来源

- 优先给**一手来源**（原始报道机构）而非聚合镜像（MSN / Yahoo 转载）
- 一条记录可以有多个来源，编号 + 换行：

```
1. https://example.com/original-a
2. https://example.com/second-outlet
```

## 工作流

```
⓪ 前置：command -v lark-cli 自检；未装 → 让用户安装
   https://github.com/larksuite/cli 并授予表格读写权限，再继续
① 读台账「当前」表最后 200 行  ← 必做，先建立"历史推过什么"的清单
② 收集本批次的候选内容（搜索优先级见下）
③ 逐条比对历史：
     - 完全推过、无新进展        → 丢弃
     - 推过、但有新进展          → 做成"补充"条目（内容里点明进展，可引用原条目日期）
     - 没推过                    → 新条目
④ 按热度排序，选出用户要的条数（默认 5–8 条）
⑤ 问用户本批次的「类型」（若用户已说明则直接用）
⑥ 定稿 → 写入「当前」表（追加到最后一个非空行之后），**写完回读校验**
⑦ 检查行数是否达阈值 → 达阈值则归档（流程见 [references/archive.md](references/archive.md)）
```

**搜索优先级**（第一条固定是 DuckDuckGo search；可被用户在团队里另行约定覆盖）：

1. **DuckDuckGo search（`ddgs`）**——固定第一优先：免 API key、无额度账单、够用
   - **如果当前 agent 是 Hermes Agent** → 用 `duckduckgo-search` 技能；**没装就先装**：

     ```bash
     hermes skills install official/research/duckduckgo-search
     ```

     然后按技能说明用 CLI（`ddgs`）：

     ```bash
     ddgs news -q "artificial intelligence" -m 8 -t d   # 新闻，近一天
     ddgs text -q "关键词" -m 5                          # 网页
     ddgs images -q "关键词" -m 10                       # 图片
     ```
   - **其他 agent**（Claude Code / Codex / OpenCode / Cursor 等）没有技能安装机制，**直接阅读官方技能文档照做**：
     https://github.com/NousResearch/hermes-agent/tree/main/optional-skills/research/duckduckgo-search
     最小可用做法：`pip install ddgs`，然后 `ddgs news -q "<主题>" -m 8 -t d`
   - 关键参数：`-m` 条数、`-t d|w|m|y` 时间窗（日/周/月/年）、`-r` 地区（如 `us-en`）、`-b` 指定后端；**JSON 落盘**要写文件名 `-o out.json`（`-o json` 不打印）
   - 偶发限流/空结果：**加大 `-m` 一次多拿**，或间隔几秒重试、换 `-b` 后端；不要并发开一堆查询
2. 宿主 agent 自带的搜索工具（如 `web_search`）——通常按次计费，`ddgs` 拿不到结果时再用
3. `curl` / 命令行 API
4. 浏览器工具——最慢，且可能干扰用户正在使用的浏览器，放最后

**热度排序**的可用信号（挑 2 个以上交叉验证，别只看一个）：

- 同一事件被多少家**独立**媒体跟进（聚合转载只算 1 家）
- 是否出现在权威媒体/通讯社（Reuters / AP / AFP / 新华社 / 央视）
- 是否进入科技/财经新闻聚合站的头条（如 Techmeme）
- 社交热榜（微博热搜、知乎热榜、B 站、抖音等）——**只当领先信号，不当事实源**

## 输出格式规范

**默认输出**（用户没提额外要求时）：**只有序号 + 一句话事实**，不要类别、不要来源、不要热度说明、不要任何多余表述。

```
1. <一句话事实>
2. <一句话事实>
```

**仅在用户明确要求时**才附加：题材类别 / 新闻类别标签、来源 URL 列表、热度排序说明、日期与覆盖时间窗说明。

## 在定时任务（cron）里跑

本技能经常被挂成每日/每班次的定时任务。定时任务**没有人在场点确认**，执行环境与交互会话不一样：

- **不能用 `execute_code`**：无人审批时它会被直接 BLOCK（报错形如 `BLOCKED: execute_code runs arbitrary local Python … Cron jobs run without a user present to approve`）。生成写入 payload、做「内容 ≤100 字」这类断言，**一律改用 `terminal` 里的 heredoc / `python -c`**。
- **要问用户的步骤必须提前定死**：「类型」这种正常流程里要问用户的字段、以及日期口径（推送日 vs 内容发生日），都得在任务 prompt 里写死——定时任务问不出问题，卡住就等于这一班次没产出。

## 参考文件（references/）

务必完整阅读，避免歧义

| 文件 | 内容 |
|---|---|
| [references/archive.md](references/archive.md) | **归档流程**：达标后新建 `归档-YYYY-MM-DD`，用 `+range-move` 跨表剪切最早那批、剩余上移压实、回读核对（含完整命令序列与阈值） |
| [references/lark-cli-cheatsheet.md](references/lark-cli-cheatsheet.md) | **lark-cli 命令速查**：本技能用到的全部 shortcut + 易错点（A1 引用加单引号、`+csv-put`/`+dim-insert` 的参数差异等） |
| [references/iptc-topics.md](references/iptc-topics.md) | **题材类别表**：IPTC Media Topics 中文 19 类（`题材类别` 列只能取自这里）+ 官方词表链接 |
| [references/source-pool.md](references/source-pool.md) | **内容来源池示例**：国内外媒体清单模板、一手来源纪律、新闻转载合规提示 |

## 踩坑记录

- **lark-cli 没装就上手**：先 `command -v lark-cli`。没有就让用户装（https://github.com/larksuite/cli）并授权表格读写——本技能**只走 lark-cli**，不用脚本替代。
- **列顺序不要写死**：不同表把「来源」放的位置不一样（模板表：`内容 | 来源 | 详细内容`），动手前先读表头，一律按表头列名定位；写死列号会把来源写进详细内容里。
- **日期跨零点写错**：凌晨跑"今天的晚报"时，`date` 先查一遍；写表前与用户确认日期口径（推送日 vs 内容发生日）。
- **日期被读成序列号**：读单元格时日期可能返回 Excel 序列号（`2026-09-13` → `46023`）；搬移行之前先抽查一行确认读到的是日期文本，别把数字搬进归档表。
- **来源列写成字面 `\n`**：写 JSON / CSV 里必须是真的换行符；写完**回读**确认单元格里是换行而不是两个字符。
- **`来源` 只贴聚合镜像**：MSN / Yahoo 转载链接会失效或改址，尽量回到原始媒体 URL。
- **行数不够**：写入超出工作表现有行数会失败；先 `+dim-insert` 加行，或建表时 `--row-count` 给够。
- **归档不要用"删行"**：删行会连带影响引用与格式；用 `+range-move` 跨表剪切 + 剩余段上移压实。
- **`+cells-clear` 是 high-risk-write**：先 `--dry-run` 看范围，再带 `--yes` 执行；不可撤销。
- **搜索热榜≠事实**：热榜只用来发现线索，事实必须回到一手来源核。
- **一条事件被多家转载 ≠ 多个来源**：算热度时按"独立媒体"去重，否则会把热度算高。
- **在定时任务里用 `execute_code`**：cron 无人审批，`execute_code` 会被 BLOCK；payload 生成与字段断言改走 `terminal` 的 heredoc / `python -c`（详见「在定时任务（cron）里跑」）。
