---
name: tokenspeed-benchmark
description: 测量任意 LLM API 的 token/s 速度指标（TTFT、生成速度、端到端吞吐）。用 when 用户要测模型速度、对比两个厂商速度、评估中转 API 快慢。
category: devops
author: dirtydamn
---

# LLM 速度基准测试（自包含技能）

测量任意 LLM API 的三个核心速度指标：TTFT、生成速度、端到端吞吐。纯 Python 标准库，**无需安装任何依赖**，任何 agent（Codex / Claude Code / OpenCode / Hermes）均可使用。

## 原理（30 秒版）

厂商 API **不会返回 token/s**，只能客户端计时测算。本技能用**流式请求**逐 chunk 解析：

| 指标 | 含义 | 算法 |
|---|---|---|
| **TTFT** | 首字延迟（你等多久才开始出字） | 发请求 → 第一个 chunk 到达的时间 |
| **生成速度** | 纯生成阶段速度（第一个字后多快） | 估算 tokens ÷（总耗时 − TTFT） |
| **端到端吞吐** | 全程体感速度（含等待） | 估算 tokens ÷ 总耗时 |

**三指标关系（通俗版，输出时必须附给用户）：**

```
你发请求
   │
   ├─ TTFT ──► 第一个字出来        (你等多久才开始，单位 ms/s)
   │             然后开始出字
   ├─ 生成速度 ─► 纯生成阶段速度     (出字多快，单位 tok/s)
   │
   └─ 端到端吞吐 ─► 全程平均速度    (含等待，体感速度，单位 tok/s)
```

> 端到端 ≈ 生成速度被 TTFT 拖累后的结果。TTFT 越大，端到端越慢。

token 估算是**近似值**（字符数 × 0.75，中文约 1 字 ≈ 0.75 token）；如需精确 token 数，用非流式请求读响应里的 `usage.completion_tokens`。

## 快速开始

```bash
# 1. 直接跑（key 从环境变量 / .env 自动读取）
python3 scripts/benchmark.py \
  --base-url https://api.example.com/v1 \
  --model deepseek/deepseek-v4-flash

# 2. 显式指定 key / 更多参数
python3 scripts/benchmark.py \
  --base-url https://api.example.com/v1 \
  --model my-model \
  --key sk-xxx \
  --rounds 3 \
  --api-mode openai       # 或 anthropic
```

## 凭据解析顺序（默认用用户当前 key）

1. CLI 参数 `--key`
2. 环境变量 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
3. `.env` 文件（`./.env`、`~/.env`、`~/.hermes/.env`）
4. **都拿不到 → 交互式询问用户**

用户也可显式指定 `--base-url --model --key --api-mode` 覆盖默认。

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--base-url` | 必填 | API 基础 URL，如 `https://api.example.com/v1` |
| `--model` | 必填 | 模型 id，如 `deepseek/deepseek-v4-flash` |
| `--key` | 自动 | API key（或走环境变量 / .env） |
| `--api-mode` | `openai` | `openai`（chat/completions）或 `anthropic`（/messages） |
| `--rounds` | `3` | 测试轮数（≥3 取中位/平均更准） |
| `--max-tokens` | `1500` | 单轮最大输出 token |
| `--prompt-file` | 内置 | 自定义提示词文件 |
| `--gap` | `10` | 轮间间隔秒数（防限流） |

## 踩坑记录

- **User-Agent 拦截**：部分中转 API（如 CommandCode）拦截 `Python-urllib/x.x`，脚本已内置伪造 `User-Agent: curl/8.4.0`。
- **流式必须**：非流式测不到 TTFT，只有总耗时。
- **token 估算是近似**：不依赖厂商 tokenizer；精确值需非流式读 `usage`。
- **单次测不准**：速度随负载波动，至少 3 轮取中位/平均。
- **轮间间隔**：连续请求会撞限流，默认 10 秒。

## 输出示例

```
=== deepseek/deepseek-v4-flash 速度测试 ===
模型: deepseek/deepseek-v4-flash | 模式: openai | 时间: 2026-08-30 14:25

轮次    TTFT(ms)    总耗时(s)      ~tokens   生成(tok/s)     端到端(tok/s)
1     1707        7.55        543       93.0          72.0
2     3391        9.70        534       84.7          55.1
3     1626        6.66        484       96.2          72.7

TTFT        平均 2241ms (最快 1626 / 最慢 3391)
生成速度    平均 91.3 tok/s (最快 96.2 / 最慢 84.7)
端到端吞吐  平均 66.6 tok/s (最快 72.7 / 最慢 55.1)

三指标关系:
- TTFT     = 首字延迟(你等多久才开始出字)
- 生成速度 = 出字速度(第一个字之后多快)
- 端到端   = 全程体感(含等待,最接近你的感受)

📊 直观感受各 tok/s 档位: https://mikeveerman.github.io/tokenspeed
   (输入你的平均 tok/s,可直观感受这个速度读起来是什么感觉)
```

## 参考

- OpenAI 兼容：`POST {base_url}/chat/completions`，流式加 `"stream": true`
- Anthropic 兼容：`POST {base_url}/messages`，流式加 `"stream": true`，头 `x-api-key` + `anthropic-version`
