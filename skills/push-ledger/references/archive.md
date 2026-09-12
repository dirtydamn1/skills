# 归档流程

阈值默认 **1000 行**（含表头）；达到或超过时把最早 **800 行**搬去 `归档-YYYY-MM-DD`，让「当前」回到 **200 条左右**。

全程用 `lark-cli` 的**跨表剪切**（`+range-move`），**不要删行**——删行会连带影响引用与格式。

## 命令序列

```bash
# 设变量，后面都好读
U="https://<租户>.feishu.cn/sheets/<token>"
SRC="当前"                # 源子表（也可用 --sheet-id）
N=1000                    # 当前总行数（含表头）
KEEP=200                  # 要保留的条数
ARCH="归档-$(date +%Y-%m-%d)"

# 1) 数清行数、确认表头与末行（先读，别猜）
lark-cli sheets +csv-get --url "$U" --sheet-name "$SRC" --range "A1:G${N}"

# 2) 新建归档子表
lark-cli sheets +sheet-create --url "$U" --title "$ARCH" --row-count 1000 --col-count 21

# 3) 表头复制过去（保持两边列一致）
lark-cli sheets +range-copy --url "$U" --sheet-name "$SRC" \
  --source-range "A1:G1" --target-sheet-id <归档表 sheet_id> --target-range "A1"

# 4) 把最早那批（示例：第 2~801 行）整体剪切到归档表
lark-cli sheets +range-move --url "$U" --sheet-name "$SRC" \
  --source-range "A2:G801" --target-sheet-id <归档表 sheet_id> --target-range "A2"

# 5) 把剩下的记录整体上移，压实（源区已被清空，不再有空洞）
lark-cli sheets +range-move --url "$U" --sheet-name "$SRC" \
  --source-range "A802:G${N}" --target-range "A2"

# 6) 清理尾部残留（可选，视残留内容而定；这是 high-risk-write，需要 --yes）
lark-cli sheets +cells-clear --url "$U" --sheet-name "$SRC" --range "A202:G${N}" --yes

# 7) 回读两边行数核对
lark-cli sheets +csv-get --url "$U" --sheet-name "$SRC" --range "A1:G210"
lark-cli sheets +csv-get --url "$U" --sheet-name "$ARCH" --range "A1:G810"
```

## 要点

- **先 dry-run 再真跑**：`+range-move` / `+cells-clear` 都支持 `--dry-run`，先看计划
- `+cells-clear` 是 `high-risk-write`，必须 `--yes`，且**不可撤销**
- 子表行数不够时先加行：`+dim-insert`（或建表时用 `--row-count` 给够）
- 归档完成后核对：`归档表行数 ≈ 表头 + 800`，`当前表行数 ≈ 表头 + 200`
- 归档表命名统一 `归档-YYYY-MM-DD`（用 `date +%Y-%m-%d` 取当天，别手写）

## 什么时候归档

- 「当前」表**含表头**达到或超过 1000 行
- 与用户约定过"当前表只留最近 200 条"时，也可按时间周期归档（如每月一次）
