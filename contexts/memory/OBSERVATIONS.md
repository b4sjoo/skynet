# Memory Observations

这是三层记忆系统的 L1/L2 层。每日观察由 `periodic_jobs/ai_heartbeat/src/v0/observer.py` 自动写入，每周由 `reflector.py` 整理和蒸馏。

## 格式说明

每个日期条目格式如下：

```
Date: YYYY-MM-DD

🔴 High: [方法论/约束] 描述
🟡 Medium: [项目状态/决策] 描述
🟢 Low: [任务流水] 描述
```

### 优先级定义

- **🔴 High**：跨项目通用的经验教训、硬性约束、影响系统架构的重大决策。永久保留，候选晋升为 axiom 或 skill。
- **🟡 Medium**：活跃项目的关键进展、技术决策背景、未来几周仍需参考的信息。
- **🟢 Low**：日常任务流水、瞬时 debug 记录、临时上下文。定期垃圾回收。

## 如何加载记忆

不要全文加载这个文件（可能很大）。按需检索：

```bash
# 搜索特定主题
grep -n "关键词" contexts/memory/OBSERVATIONS.md

# 搜索最近 N 天
grep -A 20 "Date: $(date -v-7d +%Y-%m-%d)" contexts/memory/OBSERVATIONS.md
```

或使用语义搜索做跨日期语义检索（安装 [semantic-search-skill](https://github.com/grapeot/semantic-search-skill)）。

---

<!-- 以下是记录区域，由 observer.py 自动追加 -->

Date: 2026-05-27

🔴 High: [架构约束] ai_heartbeat 系统采用"Pull, not Push"模式——trigger 脚本只提供线索（文件路径 + SOP），agentic engine 自主探索文件系统并写入 `contexts/memory/OBSERVATIONS.md`；这是 PRD §2.1 的核心设计原则，任何改动均需保持此分层。
🔴 High: [运维约束] `periodic_jobs/ai_heartbeat/src/v0/claude_runner.py` 调用 `claude --print` CLI；全无人值守 cron 运行（含 Bash find）时必须设置 `--permission-mode bypassPermissions`，否则 Bash 调用会被拒绝；`HEARTBEAT_PERMISSION_MODE` 环境变量可覆盖默认值 `acceptEdits`。
🟡 Medium: [项目里程碑] workspace 基线已建立（commit cfcd102）：context-infrastructure 模板完整落地，含三层记忆系统（L3=`rules/`，L1/L2=`contexts/memory/OBSERVATIONS.md`）、`periodic_jobs/ai_heartbeat/`（observer + reflector）、`tools/`（semantic_search、generate_image、typefully、send_email）以及完整 rules 系统（43 axioms、25+ skills）。
🟡 Medium: [技术决策] `HEARTBEAT_BACKEND` 环境变量控制后端选择：`claude`（新默认，使用本地 `claude --print` CLI）vs. `opencode`（旧后端，使用 OpenCode Server API）；`observer.py` 和 `reflector.py` 均已支持双后端切换，无需修改代码。
🟡 Medium: [运维规范] L2 Reflector（`periodic_jobs/ai_heartbeat/src/v0/reflector.py`）设计为手动触发而非 cron 自动运行——因其会直接修改 `rules/` 并重写 `contexts/memory/OBSERVATIONS.md`，每次运行后必须执行 `git diff` 人工审核；`docs/CRONTAB.md` 中的 cron 时间表仅为 Observer（每日 8:00）和 Crontab Monitor（每日 9:00）配置了自动任务，Reflector 为每周日 9:00 但需人工确认。
🟢 Low: [任务流水] `contexts/` 目录在基线状态基本为空：仅 `contexts/memory/OBSERVATIONS.md` 存在；`survey_sessions/`、`thought_review/`、`daily_records/` 均为占位目录，尚无实际内容。
🟢 Low: [任务流水] `contexts/blog/content/` 目录不存在，本日无新 Blog 文章需记录。
🟢 Low: [任务流水] Python 环境由 `uv` 管理（`pyproject.toml` + `uv.lock` + `pyrightconfig.json` 均已提交），工作区级 `.venv/` 为标准入口。
🔴 High: [方法论/约束] 并行 subagent 方法论已按 Claude Code 现实修订（`rules/skills/workflow_parallel_subagents.md`、`bestpractice_multi_agent_analysis.md`、`AGENTS.md` 模型路由节、`workflow_deep_research_survey.md`）：subagent 经 `Agent` 工具派出，`model` 仅 Claude（无 Gemini/GPT 跨 provider），subagent 不能再派 subagent（嵌套上移到主 agent 平铺），无内建共享 scratchpad（改用文件 `tmp/<session>/`），后台完成自动回传无需轮询；旧 `mcp_task`/`category`/`background_output`/`oh-my-opencode.json` 标记为 OpenCode 遗留。
