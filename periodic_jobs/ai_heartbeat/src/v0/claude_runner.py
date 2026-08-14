#!/usr/bin/env python3
"""
Claude Code (headless) backend for the AI Heartbeat trigger scripts.

observer.py / reflector.py are *trigger* scripts: they build a prompt and hand it
to an agentic engine that scans the workspace and writes the memory files itself
(PRD §2.1 — Pull, not Push). This module replaces the OpenCode Server backend
(opencode_client.py) with the locally installed, already-authenticated
`claude --print` CLI, which is an agentic runner of the same shape
(filesystem + bash + sub-agents). Standard library only — no new pip deps.

Backend selection lives in the trigger scripts via the HEARTBEAT_BACKEND env var
(default "claude"); set HEARTBEAT_BACKEND=opencode to use opencode_client instead.
"""
from __future__ import annotations

import shutil
import subprocess


def run_agent_task(
    prompt: str,
    cwd: str,
    model: str = "sonnet",
    permission_mode: str = "acceptEdits",
    allowed_tools: list[str] | None = None,
    timeout: int = 3600,
    max_budget_usd: float | None = None,
) -> tuple[bool, str]:
    """Run an agentic task with `claude --print` from inside `cwd`.

    The agent inherits Claude Code's full tool set and self-scans/writes files.

    Args:
        prompt: The full task prompt handed to the agent.
        cwd: Working directory (the workspace root); also passed via --add-dir.
        model: Alias ("sonnet"/"opus"/"haiku") or full model id.
        permission_mode: "acceptEdits" auto-accepts Edit/Write (Read/Glob/Grep are
            always allowed); "bypassPermissions" also allows Bash, needed for fully
            unattended cron runs that shell out (e.g. `find -mtime`).
        allowed_tools: Optional explicit allow-list (e.g. ["Edit", "Bash(find *)"])
            for least-privilege runs instead of bypassPermissions.
        timeout: Seconds before the run is killed (agentic tasks can be slow).
        max_budget_usd: Optional hard spend cap for the run.

    Returns:
        (ok, output) — ok is False on non-zero exit, timeout, or a missing CLI.
    """
    claude = shutil.which("claude")
    if not claude:
        return (
            False,
            "claude CLI not found on PATH. Install Claude Code, or set "
            "HEARTBEAT_BACKEND=opencode to use the OpenCode Server backend.",
        )

    cmd = [
        claude,
        "--print",
        "--model", model,
        "--permission-mode", permission_mode,
        "--add-dir", cwd,
        "--output-format", "text",
    ]
    if allowed_tools:
        cmd += ["--allowedTools", *allowed_tools]
    if max_budget_usd is not None:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    cmd.append(prompt)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"claude --print timed out after {timeout}s"
    except Exception as exc:  # surface any spawn failure to the caller
        return False, f"failed to run claude --print: {exc}"

    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, output


if __name__ == "__main__":
    # Smoke test: `python3 claude_runner.py "your prompt"` in the current directory.
    import sys
    from pathlib import Path

    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: heartbeat backend OK"
    ok, out = run_agent_task(test_prompt, cwd=str(Path.cwd()), permission_mode="default")
    print(f"[ok={ok}]\n{out}")
