"""The result type shared by every check."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Finding:
    """A single convention violation.

    Attributes:
        check: Name of the check that produced the finding.
        path: File or directory the finding is about.
        message: Human-readable explanation, including how to fix it.
        line: 1-based line number, when the finding points at a specific line.
    """

    check: str
    path: Path
    message: str
    line: int | None = None

    def render(self, root: Path) -> str:
        """Format as ``path[:line]: [check] message`` with ``path`` relative to ``root``."""
        location = (
            self.path.relative_to(root).as_posix()
            if self.path.is_relative_to(root)
            else self.path.as_posix()
        )
        if self.line is not None:
            location = f"{location}:{self.line}"
        return f"{location}: [{self.check}] {self.message}"
