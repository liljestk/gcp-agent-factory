"""Claude Code PreToolUse hook: block destructive shell commands (REQ-REPO-007).

Reads the hook payload (JSON) from stdin. Exit code 2 blocks the tool call and shows stderr
to the agent; exit code 0 allows it. Malformed payloads fail open, so a broken payload never
bricks a session. IAM and the CI pipeline remain the real controls; this guard stops
accidents early.
"""

from __future__ import annotations

import json
import re
import sys
from typing import TextIO

SHELL_TOOLS = frozenset({"Bash", "PowerShell"})

# Each pattern only looks within one simple command (stops at | ; & and newlines).
_SEGMENT = r"[^|;&\n]*"

BLOCKED: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(rf"\b(tofu|terraform)\b{_SEGMENT}\b(apply|destroy)\b"),
        "infrastructure changes go through CI, not a local apply/destroy",
    ),
    (
        re.compile(rf"\bgcloud\b{_SEGMENT}\bservice-accounts\s+keys\s+create\b"),
        "service-account keys are forbidden (INV-01)",
    ),
    (
        re.compile(rf"\bgcloud\b{_SEGMENT}\bdelete\b"),
        "deleting cloud resources is reserved for CI and humans",
    ),
    (
        re.compile(rf"\bgcloud\b{_SEGMENT}\bbilling\b{_SEGMENT}\b(unlink|disable)\b"),
        "billing changes are a kill-switch action owned by the ops pipeline",
    ),
    (
        re.compile(rf"\b(gsutil|gcloud\s+storage)\b{_SEGMENT}\brm\b"),
        "deleting bucket objects is reserved for CI and humans",
    ),
    (
        re.compile(rf"\bbq\s+rm\b{_SEGMENT}"),
        "deleting BigQuery resources is reserved for CI and humans",
    ),
    (
        re.compile(rf"\bgit\b{_SEGMENT}\bpush\b{_SEGMENT}(--force|\s-[a-zA-Z]*f\b|\s\+\S)"),
        "force-pushing rewrites shared history",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(/|~|\$HOME)(\s|$)"),
        "recursive delete of a root or home directory",
    ),
)


def find_violation(command: str) -> str | None:
    """Return the reason ``command`` is blocked, or ``None`` if it is allowed."""
    for pattern, reason in BLOCKED:
        if pattern.search(command):
            return reason
    return None


def evaluate(payload: object) -> str | None:
    """Return a block reason for a PreToolUse payload, or ``None`` to allow it."""
    if not isinstance(payload, dict) or payload.get("tool_name") not in SHELL_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return None
    return find_violation(command)


def main(stdin: TextIO = sys.stdin, stderr: TextIO = sys.stderr) -> int:
    """Run the hook and return its exit code (2 = block, 0 = allow)."""
    try:
        payload = json.load(stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    reason = evaluate(payload)
    if reason is None:
        return 0
    stderr.write(
        f"Blocked by .claude/hooks/guard_bash.py: {reason}. "
        "Ask a human to run it, or use the matching CI workflow.\n",
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
