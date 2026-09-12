# dirtydamn/skills

dirtydamn 的开源 Agent Skills 集合。所有技能遵循 [Agent Skills 规范](https://github.com/agentskills/agentskills)，兼容 Claude Code、Codex、OpenCode、Cursor 等支持 SKILL.md 的 agent。

## 安装

使用 [skills CLI](https://github.com/vercel-labs/skills)（Vercel 开源生态）：

```bash
# 查看全部技能
npx skills add dirtydamn1/skills --list

# 安装指定技能
npx skills add dirtydamn1/skills --skill youdaonote-export

# 安装到指定 agent（如 Claude Code）
npx skills add dirtydamn1/skills --skill youdaonote-export -a claude-code

# 安装全部技能
npx skills add dirtydamn1/skills --skill '*'
```

> 国内网络访问 GitHub 不稳定时，先配置代理再执行。

## 技能列表

| 技能 | 说明 |
|---|---|
| [push-ledger](skills/push-ledger/SKILL.md) | 推送台账：记录推过什么、查重、识别可补充的后续进展、自动归档；适用于新闻简报、行业简报、竞品动态、政策变化等各类自定义通知监测场景 |
| [hermes-contribution-workflow](skills/hermes-contribution-workflow/SKILL.md) | Hermes Agent 源码 fork 开发提 PR 工作流：双 remote 配置、fix 分支命名、cherry-pick 重生循环 |
| [tokenspeed-benchmark](skills/tokenspeed-benchmark/SKILL.md) | 测量任意 LLM API 的 token/s 速度指标（TTFT、生成速度、端到端吞吐），支持 OpenAI/Anthropic 兼容接口，跨 agent 通用 |
| [youdaonote-export](skills/youdaonote-export/SKILL.md) | 有道云笔记一键导出/备份/迁移为本地 Markdown（自包含，无需联网拉代码） |

## 目录结构

```
skills/
└── <技能名>/
    ├── SKILL.md          # 技能定义（frontmatter 必须含 name + description）
    └── scripts/          # 可选的配套脚本/项目
```

支持分类层级：`skills/<分类>/<技能名>/SKILL.md`（分类目录本身不能有 SKILL.md）。

## 贡献

1. Fork 本仓库
2. 在 `skills/` 下新建技能目录（参照 [Agent Skills 规范](https://github.com/agentskills/agentskills)）
3. SKILL.md 的 frontmatter 必须包含 `name` 和 `description`
4. 提交 PR

## License

[MIT](LICENSE) © dirtydamn
