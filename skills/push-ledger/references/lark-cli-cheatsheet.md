# lark-cli 命令速查（本技能用到的）

前置：`command -v lark-cli` 通、`lark-cli auth status` 为 ready、表格读写 scope 已开通并发布版本。

```bash
U="https://<租户>.feishu.cn/sheets/<token>"

# 看工作簿有哪些子表、行列数
lark-cli sheets +workbook-info --url "$U"

# 读一段（查重、核对、回读）
lark-cli sheets +csv-get --url "$U" --sheet-name "当前" --range "A1:G200"

# 读单元格详情（值 / 公式 / 样式）
lark-cli sheets +cells-get --url "$U" --sheet-name "当前" --range "A1:G9" --include value

# 写一段（结构化写入：值 / 样式 / 批注都能带，跟 --range 的尺寸严格对应）
lark-cli sheets +cells-set --url "$U" --sheet-name "当前" --range "A3:G9" --cells - < payload.json

# 平铺纯文本 CSV 到指定锚点（列里没有需字面保真的数字/日期时最快；右下角按 CSV 尺寸自动推断）
lark-cli sheets +csv-put --url "$U" --sheet-name "当前" --start-cell "A3" --csv - < rows.csv

# 查找 / 替换（按关键词查"是否推过"）
lark-cli sheets +cells-search --url "$U" --sheet-name "当前" --find "英伟达"
lark-cli sheets +cells-replace --url "$U" --sheet-name "当前" --find "旧" --replace "新"

# 新建子表 / 跨表剪切 / 清空范围 / 加行
lark-cli sheets +sheet-create  --url "$U" --title "归档-2026-09-13" --row-count 1000 --col-count 21
lark-cli sheets +range-move    --url "$U" --sheet-name "当前" --source-range "A2:G801" --target-sheet-id <sid> --target-range "A2"
lark-cli sheets +range-copy    --url "$U" --sheet-name "当前" --source-range "A1:G1" --target-sheet-id <sid> --target-range "A1"
lark-cli sheets +cells-clear   --url "$U" --sheet-name "当前" --range "A202:G1000" --yes
lark-cli sheets +dim-insert    --url "$U" --sheet-name "当前" --position 1001 --count 200 --inherit-style before
```

## 易错点

- 写 `--range` / `--source-range` 等含 `!` 的 A1 引用时**整段用单引号**包住（防 shell 历史展开）
- payload 大或含换行时用 `--cells - < 文件` 走 stdin，别硬拼命令行
- `+csv-put` 只有 `--start-cell`（单格锚点）+ `--csv`，**没有 `--range`**
- `+dim-insert` 用 `--position` + `--count`，**没有 `--range`**
- `+csv-get` 的行号前缀（`[row=N]`）用于定位真实行号，别当成内容
- 同一 shortcut 反复调用同一区域时，先 `--dry-run` 看请求再执行
- 不确定 sheet_id 时先 `+workbook-info`，不要猜 `Sheet1`
