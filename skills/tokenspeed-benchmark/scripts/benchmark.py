#!/usr/bin/env python3
"""
LLM speed benchmark — measure TTFT, generation speed, end-to-end throughput.

Usage:
  python3 benchmark.py --base-url https://api.example.com/v1 \
      --key sk-xxx --model my-model [--rounds 3] [--prompt-file p.txt]

Credential resolution (in order):
  1. --key / --api-key CLI arg
  2. env var OPENAI_API_KEY / ANTHROPIC_API_KEY / <PROVIDER>_API_KEY
  3. .env file (./.env, ~/.env, ~/.hermes/.env) lines KEY=value
  4. If nothing found, prompt interactively.

OpenAI-compatible by default; use --api-mode anthropic for Anthropic Messages.
"""

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from pathlib import Path

# Chinese chars -> token estimate factor (approximate; adjust for English/code)
TOKEN_PER_CHAR = 0.75
DEFAULT_ROUNDS = 3
ROUND_GAP_SECONDS = 10


def resolve_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(var)
        if val:
            return val
    # scan .env files
    for env_path in (Path(".env"), Path.home() / ".env", Path.home() / ".hermes" / ".env"):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") and v.strip():
                return v.strip()
    return input("No API key found. Please provide your API key: ").strip()


def build_request(base_url, key, model, prompt, api_mode, max_tokens):
    if api_mode == "anthropic":
        url = base_url.rstrip("/") + "/messages"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "curl/8.4.0",  # some relays 403 Python-urllib UA
        }
    else:
        url = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "curl/8.4.0",
        }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    return req


def parse_stream_chunk(line: str, api_mode: str) -> str:
    """Extract delta text from one SSE line. Returns '' for non-content lines."""
    line = line.strip()
    if not line.startswith("data:"):
        return ""
    payload = line[5:].strip()
    if payload == "[DONE]":
        return ""
    try:
        d = json.loads(payload)
    except Exception:
        return ""
    if api_mode == "anthropic":
        # Anthropic SSE: event: content_block_delta / data: {"delta":{"text":"..."}}
        delta = d.get("delta") or {}
        return delta.get("text") or ""
    choices = d.get("choices") or []
    if not choices:
        return ""
    delta = (choices[0].get("delta") or {}) or (choices[0].get("message") or {})
    return delta.get("content") or ""


def run_once(base_url, key, model, prompt, api_mode, max_tokens):
    req = build_request(base_url, key, model, prompt, api_mode, max_tokens)
    t0 = time.monotonic()
    ttft = None
    content_chars = 0
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            if ttft is None:
                ttft = time.monotonic() - t0
            text = parse_stream_chunk(raw.decode("utf-8", errors="ignore"), api_mode)
            if text:
                content_chars += len(text)
    t1 = time.monotonic()
    elapsed_total = t1 - t0
    gen_elapsed = elapsed_total - (ttft or 0)
    est_tokens = int(content_chars * TOKEN_PER_CHAR)
    gen_speed = est_tokens / gen_elapsed if gen_elapsed > 0 else 0.0
    e2e_speed = est_tokens / elapsed_total if elapsed_total > 0 else 0.0
    return {
        "ttft_ms": (ttft or 0) * 1000,
        "total_s": elapsed_total,
        "tokens": est_tokens,
        "gen_speed": gen_speed,
        "e2e_speed": e2e_speed,
    }


def main():
    ap = argparse.ArgumentParser(description="LLM speed benchmark (TTFT / gen / e2e)")
    ap.add_argument("--base-url", required=True, help="API base URL, e.g. https://api.example.com/v1")
    ap.add_argument("--model", required=True, help="Model id, e.g. deepseek/deepseek-v4-flash")
    ap.add_argument("--key", dest="key", default=None, help="API key (or env OPENAI_API_KEY)")
    ap.add_argument("--api-mode", default="openai", choices=["openai", "anthropic"])
    ap.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help=f"Rounds (default {DEFAULT_ROUNDS})")
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--prompt-file", default=None, help="File with prompt text (default: built-in)")
    ap.add_argument("--gap", type=int, default=ROUND_GAP_SECONDS, help="Seconds between rounds")
    args = ap.parse_args()

    key = resolve_key(args.key)
    if not key:
        print("No API key available. Use --key or set OPENAI_API_KEY.", file=sys.stderr)
        sys.exit(2)

    prompt = "请用中文写一篇关于人工智能发展历史的科普文章，大约500字，包括起源、发展阶段、当前应用和未来展望。请分段落详细展开。"
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")

    print(f"=== {args.model} 速度测试 ===")
    print(f"模型: {args.model} | 模式: {args.api_mode} | 时间: {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 84)
    print(f"{'轮次':<6}{'TTFT(ms)':<12}{'总耗时(s)':<12}{'~tokens':<10}{'生成(tok/s)':<14}{'端到端(tok/s)'}")
    print("-" * 84)

    results = []
    for i in range(args.rounds):
        try:
            r = run_once(args.base_url, key, args.model, prompt, args.api_mode, args.max_tokens)
            results.append(r)
            print(f"{i+1:<6}{r['ttft_ms']:<12.0f}{r['total_s']:<12.2f}{r['tokens']:<10}{r['gen_speed']:<14.1f}{r['e2e_speed']:.1f}")
        except Exception as e:
            print(f"{i+1:<6}失败 - {e}")
        if i < args.rounds - 1:
            time.sleep(args.gap)

    print("=" * 84)
    if results:
        ttf = [r["ttft_ms"] for r in results]
        gs = [r["gen_speed"] for r in results]
        e2 = [r["e2e_speed"] for r in results]
        print(f"TTFT        平均 {statistics.mean(ttf):.0f}ms (最快 {min(ttf):.0f} / 最慢 {max(ttf):.0f})")
        print(f"生成速度    平均 {statistics.mean(gs):.1f} tok/s (最快 {max(gs):.1f} / 最慢 {min(gs):.1f})")
        print(f"端到端吞吐  平均 {statistics.mean(e2):.1f} tok/s (最快 {max(e2):.1f} / 最慢 {min(e2):.1f})")
        print()
        print("三指标关系:")
        print("- TTFT     = 首字延迟(你等多久才开始出字)")
        print("- 生成速度 = 出字速度(第一个字之后多快)")
        print("- 端到端   = 全程体感(含等待,最接近你的感受)")
        print()
        print("📊 直观感受各 tok/s 档位: https://mikeveerman.github.io/tokenspeed")
        print("   (输入你的平均 tok/s,可直观感受这个速度读起来是什么感觉)")


if __name__ == "__main__":
    main()
