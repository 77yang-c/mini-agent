"""Shell 工具：默认需要用户审批。"""

from __future__ import annotations

import re
import subprocess
from typing import Any

from tools.base import Tool, ToolContext, ToolResult

_BLOCKED = re.compile(
    r"(?i)\brm\s+-[a-z]*rf\b|\bdel\s+/[sf]\b|\bformat\s+|\b(shutdown|reboot)\b|"
    r"Remove-Item.*-Recurse|\biex\b|Invoke-Expression"
)


class RunShellTool(Tool):
    name = "run_shell"
    description = "在工作区执行 shell 命令。危险命令会被拦截；普通命令可能需用户批准。"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout_sec": {"type": "integer", "default": 60},
        },
        "required": ["command"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = str(args.get("command") or "").strip()
        if not command:
            return ToolResult(ok=False, content="空命令")
        if _BLOCKED.search(command):
            return ToolResult(ok=False, content="命令被安全策略拦截")

        if not ctx.auto_approve_shell:
            if ctx.approve_shell is None or not ctx.approve_shell(command):
                return ToolResult(ok=False, content="用户拒绝执行该命令")

        timeout = int(args.get("timeout_sec") or 60)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=ctx.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, content=f"超时（{timeout}s）")
        except OSError as e:
            return ToolResult(ok=False, content=str(e))

        parts = []
        if proc.stdout:
            parts.append(proc.stdout)
        if proc.stderr:
            parts.append("--- stderr ---\n" + proc.stderr)
        parts.append(f"[exit_code={proc.returncode}]")
        return ToolResult(ok=proc.returncode == 0, content="\n".join(parts).strip())
