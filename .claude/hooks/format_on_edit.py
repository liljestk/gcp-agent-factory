"""Claude Code PostToolUse hook: format the file that was just edited.

Python files go through ``ruff format`` (via uv) and OpenTofu files through ``tofu fmt``,
but only when those tools are installed. The hook never blocks: it always exits 0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TextIO

TOFU_SUFFIXES = (".tf", ".tfvars", ".tftest.hcl")
TIMEOUT_SECONDS = 30


def formatter_for(path: str) -> list[str] | None:
    """Return the formatter command for ``path``, or ``None`` if none applies or is installed."""
    if path.endswith(".py"):
        uv = shutil.which("uv")
        return [uv, "run", "--frozen", "--quiet", "ruff", "format", path] if uv else None
    if path.endswith(TOFU_SUFFIXES):
        tofu = shutil.which("tofu")
        return [tofu, "fmt", path] if tofu else None
    return None


def edited_path(payload: object) -> str | None:
    """Extract the edited file path from a PostToolUse payload."""
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path")
    return path if isinstance(path, str) and path else None


def main(stdin: TextIO = sys.stdin) -> int:
    """Run the hook; always returns 0 so formatting problems never block an edit."""
    try:
        payload = json.load(stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    path = edited_path(payload)
    if path is None or not Path(path).is_file():
        return 0
    command = formatter_for(path)
    if command is None:
        return 0
    try:
        # Fixed tool resolved via shutil.which; the path comes from Claude's own edit payload.
        subprocess.run(command, check=False, capture_output=True, timeout=TIMEOUT_SECONDS)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
