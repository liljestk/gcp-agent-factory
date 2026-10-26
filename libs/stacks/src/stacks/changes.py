"""The files a change touches, read from git so renames and unusual names can't hide."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

from stacks.errors import StacksError

if TYPE_CHECKING:
    from pathlib import Path

COMMIT_PATTERN: Final = re.compile(r"^[0-9a-f]{7,64}$")


def changed_paths(root: Path, base: str) -> list[str]:
    """Return every path changed between ``base`` and ``HEAD``, both sides of each rename.

    Uses ``git diff --no-renames -z``: a rename appears as a delete plus an add, and ``-z``
    prints names raw, so non-ASCII and quoted names match the catalog.

    Raises:
        StacksError: ``base`` isn't a commit SHA, git is missing, or git fails (for example a
            shallow clone without the merge base). An unknown change never looks like none.
    """
    if not COMMIT_PATTERN.match(base):
        message = f"--base must be a commit SHA, not {base!r}"
        raise StacksError(message)
    git = shutil.which("git")
    if git is None:
        message = "git is not on PATH"
        raise StacksError(message)
    command = [git, "diff", "--name-only", "--no-renames", "-z", f"{base}...HEAD"]
    # The executable is resolved above and the only variable argument is a validated SHA.
    result = subprocess.run(command, cwd=root, capture_output=True, check=False)  # noqa: S603
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        message = f"git diff {base}...HEAD failed: {detail}"
        raise StacksError(message)
    output = result.stdout.decode("utf-8", errors="surrogateescape")
    return [path for path in output.split("\0") if path]
