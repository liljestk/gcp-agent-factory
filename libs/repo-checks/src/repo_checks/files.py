"""File discovery that skips generated, vendored and cache directories."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".terraform",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
        "dist",
        "build",
    },
)


def iter_files(root: Path, suffixes: tuple[str, ...]) -> Iterator[Path]:
    """Yield files under ``root`` whose names end with one of ``suffixes``, in sorted order."""
    for dirpath, dirnames, filenames in root.walk():
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        for name in sorted(filenames):
            if name.endswith(suffixes):
                yield dirpath / name
