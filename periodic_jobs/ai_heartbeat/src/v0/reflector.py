#!/usr/bin/env python3
"""
L2 Reflector Agent (Trigger Script)

Drives an agentic engine to read OBSERVATIONS.md, promote durable lessons into
rules/, and garbage-collect the memory file. This edits L3 rules, so it is meant
to be run manually and reviewed via `git diff` -- NOT auto-run in cron.

Backend selected by HEARTBEAT_BACKEND (default "claude"). Paths are portable.
"""
import os
from datetime import datetime
from pathlib import Path

# src/v0/reflector.py -> parents[4] == workspace root
ROOT_DIR = Path(__file__).resolve().parents[4]
KNOWLEDGE_BASE = ROOT_DIR / "periodic_jobs" / "ai_heartbeat" / "docs" / "KNOWLEDGE_BASE.md"
OBSERVATIONS_PATH = ROOT_DIR / "contexts" / "memory" / "OBSERVATIONS.md"

PROMPT_TEMPLATE = """\
执行记忆系统的"反思与晋升"(L2 Reflector) 任务。
【工作区根目录】：{root_dir}
【SOP】：{kb_path}

步骤：
1. 读取 `{observations_path}`，分析 🔴 和高优 🟡 条目。
2. 将具有普适性的内容晋升到 `rules/`，按职责边界分类：
   - `rules/SOUL.md`: Agent 身份与核心价值观
   - `rules/USER.md`: 用户画像与人生哲学
   - `rules/COMMUNICATION.md`: 沟通风格（仅限沟通，不含技术知识）
   - `rules/WORKSPACE.md`: 目录路由
   - `rules/skills/`: 技术方法论、工作流、最佳实践
3. GC：重写 `{observations_path}`，删除已晋升及过期的 🟢 记录。

晋升门槛：跨项目通用 + 多次验证 + 有明确适用场景。
用 Read / Edit / Write 工具修改文件。完成后回复简短的晋升汇报（哪些观测点变成了正式规则）。
"""


def _run_opencode(prompt, model_id, title):
    """Legacy backend: drive an OpenCode Server session (lazy-imported)."""
    from opencode_client import OpenCodeClient

    client = OpenCodeClient()
    session_id = client.create_session(title)
    if not session_id:
        return False, "OpenCode: failed to create session"
    client.send_message(session_id, prompt, model_id=model_id)
    print("Waiting for session to complete (sync mode)...")
    client.wait_for_session_complete(session_id)
    return True, f"OpenCode task complete (session {session_id})."


def main():
    import argparse

    parser = argparse.ArgumentParser(description="L2 Reflector Agent")
    parser.add_argument("--model", default=os.getenv("HEARTBEAT_REFLECTOR_MODEL", "opus"),
                        help="Model alias or id (default: opus)")
    parser.add_argument("--backend", default=os.getenv("HEARTBEAT_BACKEND", "claude"),
                        choices=["claude", "opencode"], help="Execution backend")
    parser.add_argument("--permission-mode", default=os.getenv("HEARTBEAT_PERMISSION_MODE", "acceptEdits"),
                        help="claude backend permission mode")
    args = parser.parse_args()

    if not OBSERVATIONS_PATH.exists():
        print(f"No OBSERVATIONS.md at {OBSERVATIONS_PATH}; nothing to reflect on.")
        return

    prompt = PROMPT_TEMPLATE.format(
        root_dir=ROOT_DIR, kb_path=KNOWLEDGE_BASE, observations_path=OBSERVATIONS_PATH,
    )
    title = f"Heartbeat L2 Reflector - {datetime.now().strftime('%Y-%m-%d')}"

    print(f"Triggering L2 Reflector via backend={args.backend}, model={args.model}...")
    print("NOTE: this edits rules/ and rewrites OBSERVATIONS.md -- review with `git diff` afterwards.")
    if args.backend == "opencode":
        ok, msg = _run_opencode(prompt, args.model, title)
    else:
        from claude_runner import run_agent_task
        ok, msg = run_agent_task(prompt, cwd=str(ROOT_DIR), model=args.model,
                                 permission_mode=args.permission_mode)

    print(msg)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
