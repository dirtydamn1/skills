---
name: hermes-contribution-workflow
description: Hermes Agent 源码 fork 开发提 PR（双 remote、fix 分支、cherry-pick 重生）。用 when 要改 Hermes Agent 源码、修 bug 提 PR 或维护 fix 分支。
category: hermes
author: dirtydamn
---

# Hermes Agent 源码 fork 开发提 PR 工作流

给 Hermes Agent 修 bug、提 PR 的标准流程。核心是**单仓库双 remote + fix 分支**，保证日常使用稳定、开发隔离、可无痛升级。

> ## ⚠️ 必读：官方 Contributing 文档
> **提 PR 前必须先完整阅读官方贡献指南：**
> **https://hermes-agent.nousresearch.com/docs/developer-guide/contributing**
>
> 涵盖：开发环境搭建、测试运行（`scripts/run_tests.sh`）、代码风格、Windows 兼容检查（`scripts/check-windows-footguns.py`）、**分支命名规范**、**PR 描述要求**、**Conventional Commits 提交规范**（`<type>(<scope>): <desc>`）、MIT 许可声明。
>
> 本 skill 的流程、命名、提交规范均以该文档为准；两者冲突时以官方文档为准。

## 一、双 remote 共存配置（一次性）

前提：Hermes 由官方 install.sh 安装到 `~/.hermes/hermes-agent`，`origin` 已指向官方仓库。

```bash
# 1. 先去 GitHub fork 官方仓库（只需 main 分支）
#    https://github.com/NousResearch/hermes-agent → Fork 到自己账号

# 2. 进入本地 Hermes 仓库
cd ~/.hermes/hermes-agent

# 3. 添加 myfork remote（指向你的 fork，用你自己的 GitHub 账号）
git remote add myfork https://github.com/<你的账号>/hermes-agent.git

# 4. 确认
git remote -v
# origin   → https://github.com/NousResearch/hermes-agent.git (官方)
# myfork   → https://github.com/<你的账号>/hermes-agent.git   (你的 fork)

# 5. 拉取 fork 的 main
git fetch myfork main
```

| remote | 指向 | 用途 |
|---|---|---|
| `origin` | 官方 NousResearch/hermes-agent | **永远保持官方**；`hermes update` 从它拉取 |
| `myfork` | 你的 fork | 只用于 push fix 分支、提 PR |

**铁律：origin 永不改为你的 fork。** `hermes update` 的源码逻辑：有 upstream remote 就从 upstream 拉，否则从 origin 拉。保持 origin=官方最安全，update 永远不会误拉你的 fork。fork 用独立名字 `myfork`（不要用 upstream/origin 命名，避免 update 误拉）。

## 二、提 PR 标准顺序（每次都要走）

以下命令**必须由用户亲自执行**，agent 只提供命令、定义 fix 分支名。

```bash
# 1. 先更新到官方最新，确认 bug 是否已修复
hermes update

# 2. 若 bug 仍存在：同步 fork 仓库的 main 与官方一致
#    （GitHub 网页 fork 仓库 → Sync fork；或本地:）
git fetch myfork main

# 3. 从 fork 的 main 拉取 fix 分支（不是本地 main）
git checkout -b fix/<描述> myfork/main

# 4. 重启 gateway 保证正常使用，然后修复 bug
#    改代码 → 测试（源码改动需重启 gateway 才生效）

# 5. 推送到远端
git push myfork fix/<描述>

# 6. 去 GitHub 提 PR
#    https://github.com/NousResearch/hermes-agent → Pull requests
#    → New pull request → compare across forks
#    → head 选 <你的账号>:fix/<描述> → Create PR
```

## 三、fix 分支命名规范

官方 CONTRIBUTING.md 明确 + 实际 PR 主流模式：

| 类型 | 命名 | 示例 |
|---|---|---|
| Bug 修复 | `fix/<描述>` | `fix/telegram-rich-messages` |
| 新功能 | `feat/<描述>` | `feat/gemini-3-7-flash` |
| 维护者个人 | `<名字>/<描述>` | `valor/windows-secret-acls` |

- 描述用**短横线连接、小写**（不用下划线/驼峰）
- PR 标题 = 提交信息风格：`fix(作用域): 描述`（英文，国际化仓库）
- 例：`fix(telegram): render pipe tables via sendRichMessage`

## 四、日常使用与 PR 未合并期间的平衡

| 场景 | 做法 |
|---|---|
| PR 已合并 | 切回 main → `hermes update` → main 自动含修复 |
| PR 未合并，想用修复 | 留在 fix 分支跑（期间**不能** `hermes update`，会被 stash/切走） |
| PR 未合并，等不及 | 切回 main 跑官方版 |
| main 更新后 fix 过时 | 切回 main 更新 → 在 fix 分支 cherry-pick 原提交重生 |

**fix 分支重生**（main 更新后旧 fix 过时，PR 未合并）：

```bash
git checkout main && hermes update        # main 到官方最新（fix 改动不在，PR 未合）
git checkout fix/<描述>
git cherry-pick <原fix的commit>           # 最干净；或 git rebase main / git merge main
# 解冲突后：
git push myfork fix/<描述>                # 推送
# PR 自动更新
```

## 五、要点与踩坑

- **大仓库禁裸 `git fetch origin`**——hermes-agent 仓库巨大，裸 fetch 会拉全部分支+tags。必须指定单分支：`git fetch origin main` 或 `git fetch myfork fix/xxx`。
- **main 永远干净 = 官方**；所有改动只在 fix 分支。
- fix 改动不丢：cherry-pick（最干净）/ rebase / merge 带到新 main 上重生。
- Hermes 是解释型 Python，gateway 跑当前 checkout 分支；切分支/更新后**必须重启 gateway**（源码更新但 gateway 旧进程 → 新旧代码混合 ImportError）。
- `hermes update` 在 detached HEAD（手动 checkout 到 tag）时会自动切回分支再更新；日常跟 main 即可，官方没有独立 stable 分支，稳定性靠 release tag（v2026.x.x）但 tag 不用于日常 update。
- 版本模型：git tag = 发布快照（如 v2026.8.31）；main = 滚动开发（版本号不变但提交持续累积，可能有大量提交同属一个未发布版本号）。
- 网络受限（如 GitHub 被墙）时 git 操作走代理；凭据用环境变量/一次性传入，勿落盘明文。

## 相关

- 日常批量重启 gateway：hermes-gateway-batch skill（自带终端执行）。
- 官方贡献指南（必读）：https://hermes-agent.nousresearch.com/docs/developer-guide/contributing
- 官方仓库 CONTRIBUTING.md：https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md
