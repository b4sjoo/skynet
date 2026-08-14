#!/usr/bin/env python3
"""
L1 Observer Agent (Trigger Script)

Hands an agentic engine a "scan the workspace and append today's observations"
task and lets it self-explore + persist to contexts/memory/OBSERVATIONS.md.

Backend is selected by HEARTBEAT_BACKEND (default "claude" -> claude_runner;
"opencode" -> opencode_client.OpenCodeClient). Paths are derived from this file's
location, so the script is portable (no hard-coded absolute workspace path).
"""
import os
from datetime import datetime
from pathlib import Path

# src/v0/observer.py -> parents[4] == workspace root
ROOT_DIR = Path(__file__).resolve().parents[4]
KNOWLEDGE_BASE = ROOT_DIR / "periodic_jobs" / "ai_heartbeat" / "docs" / "KNOWLEDGE_BASE.md"
OBSERVATIONS_PATH = ROOT_DIR / "contexts" / "memory" / "OBSERVATIONS.md"

PROMPT_TEMPLATE = """\
【目标】：执行观测记忆提取并直接持久化到磁盘。
【基准日期】：{target_date}
【工作区根目录】：{root_dir}

【幂等性约束】：在执行任何写入前，**必须先**读取 `{observations_path}`，检查是否已存在 `Date: {target_date}` 的条目。若存在，**不要做任何文件修改**，直接回复「Entry for {target_date} already exists, skipping」即可。

【SOP 路径】：{kb_path}

【任务内容】：
1. **获取 Context**：阅读上述 SOP 以及其中引用的 L3 约束文件（`AGENTS.md`、`rules/` 下的规范）。
2. **幂等性检查**：读取 `{observations_path}`，若已有 `Date: {target_date}` 则跳过后续步骤。
3. **扫描与过滤**：用 Read / Glob / Grep 扫描工作区根目录（`{root_dir}`）下与 {target_date} 相关的变动和状态。若有 Bash 权限，可用 `find . -mtime -1` 辅助。对 `contexts/blog/content/` 下的文章，必须读 Markdown header 的 `Date` 字段，仅当为 {target_date} 时才算新内容，忽略仅格式重排。忽略 `contexts/daily_records/`。
4. **写入记忆**：用 Read 读取 `{observations_path}`，把针对 {target_date} 的 🔴 🟡 🟢 观测**追加到文件末尾**，用 Edit 或 Write 工具保存（不要依赖 shell 重定向，以便受限权限下也能写）。
5. **范围约束**：**仅执行 L1 Observer 任务**。不要执行 L2 Reflector（不修改 `rules/` 下任何文件，不做规则晋升或垃圾回收）。
6. **格式规范**：
   - 日期 Header 严格用 `Date: {target_date}`（Date 首字母大写，冒号后空格，ISO 日期）。
   - 提到文件或目录时用相对根目录的完整路径（如 `rules/skills/workflow_deep_research_survey.md`），不要只写文件名。
7. **汇报**：完成后回复一个简短的 Walkthrough（处理了什么、基于 Metadata 过滤掉多少噪音）。
"""


def _run_opencode(prompt, model_id, title, delete_after):
    """Legacy backend: drive an OpenCode Server session. Lazy-imported so the
    default claude path needs neither `requests` nor `python-dotenv`."""
    from opencode_client import OpenCodeClient

    client = OpenCodeClient()
    session_id = client.create_session(title)
    if not session_id:
        return False, "OpenCode: failed to create session"
    client.send_message(session_id, prompt, model_id=model_id)
    print("Waiting for session to complete (sync mode)...")
    client.wait_for_session_complete(session_id)
    if delete_after and client.delete_session(session_id):
        return True, f"OpenCode task complete (session {session_id} deleted)."
    return True, f"OpenCode task complete (session {session_id})."


def main():
    import argparse

    parser = argparse.ArgumentParser(description="L1 Observer Agent")
    parser.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Target date (YYYY-MM-DD)")
    parser.add_argument("--model", default=os.getenv("HEARTBEAT_OBSERVER_MODEL", "sonnet"),
                        help="Model alias or id (default: sonnet)")
    parser.add_argument("--backend", default=os.getenv("HEARTBEAT_BACKEND", "claude"),
                        choices=["claude", "opencode"], help="Execution backend")
    parser.add_argument("--permission-mode", default=os.getenv("HEARTBEAT_PERMISSION_MODE", "acceptEdits"),
                        help="claude backend permission mode (acceptEdits|bypassPermissions|...)")
    parser.add_argument("--no-delete", action="store_true",
                        help="opencode backend: keep session after completion")
    args = parser.parse_args()

    target_date = args.date

    # Idempotency: skip if entry for target_date already exists.
    if OBSERVATIONS_PATH.exists():
        if f"Date: {target_date}" in OBSERVATIONS_PATH.read_text(encoding="utf-8"):
            print(f"Idempotent skip: entry for {target_date} already exists in OBSERVATIONS.md")
            return

    prompt = PROMPT_TEMPLATE.format(
        target_date=target_date,
        root_dir=ROOT_DIR,
        kb_path=KNOWLEDGE_BASE,
        observations_path=OBSERVATIONS_PATH,
    )

    print(f"Triggering L1 Observer for {target_date} via backend={args.backend}, model={args.model}...")
    if args.backend == "opencode":
        ok, msg = _run_opencode(prompt, args.model,
                                f"Heartbeat L1 - {target_date}", not args.no_delete)
    else:
        from claude_runner import run_agent_task
        ok, msg = run_agent_task(prompt, cwd=str(ROOT_DIR), model=args.model,
                                 permission_mode=args.permission_mode)

    print(msg)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
