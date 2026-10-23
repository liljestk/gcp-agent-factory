"""Coverage exclusions must be justified (REQ-REPO-004)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from repo_checks.files import iter_files
from repo_checks.findings import Finding

if TYPE_CHECKING:
    from pathlib import Path

CHECK = "pragmas"
PRAGMA = re.compile(r"#\s*pragma:\s*no\s+(?:cover|branch)\b(?P<rest>.*)$")
JUSTIFICATION = re.compile(r"^\s*--\s*\S")


def check_pragmas(root: Path) -> list[Finding]:
    """Every coverage-exclusion pragma in Python code is followed by ``-- <reason>``."""
    findings: list[Finding] = []
    for path in iter_files(root, (".py",)):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = PRAGMA.search(line)
            if match is not None and not JUSTIFICATION.match(match.group("rest")):
                findings.append(
                    Finding(
                        CHECK,
                        path,
                        "coverage exclusion needs a reason after ' -- ' on the same line",
                        number,
                    ),
                )
    return findings
