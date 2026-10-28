"""Local module references between OpenTofu root modules and reusable modules.

The matrix is only as good as this graph, so it fails closed: a source it can't resolve to a
literal path inside the repository, a file it can't parse and any symlink raise ``StacksError``
instead of being skipped.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final

from stacks.errors import StacksError
from stacks.hcl import CONFIG_PATTERNS, load_config

if TYPE_CHECKING:
    from pathlib import Path

LOCAL_PREFIXES: Final = ("./", "../")


def local_modules(root: Path, directory: str) -> frozenset[str]:
    """Return the repo-relative directories of every local module ``directory`` uses.

    References are followed transitively and cycles are ignored.

    Raises:
        StacksError: A module source isn't a literal path inside the repository, a file can't
            be read or parsed, or a directory or file on the way is a symlink.
    """
    seen: set[str] = set()
    pending = [directory]
    while pending:
        current = pending.pop()
        for source in module_sources(root, current):
            target = join_path(current, source)
            if target is None:
                message = f"{current}: module source {source!r} leaves the repository"
                raise StacksError(message)
            if target != directory and target not in seen:
                seen.add(target)
                pending.append(target)
    return frozenset(seen)


def module_sources(root: Path, directory: str) -> list[str]:
    """Return the local module sources (``./…`` or ``../…``) used in ``directory``.

    Registry and git sources are left out; ``repo-checks tofu-safety`` rejects them.
    """
    path = root / directory
    if path.is_symlink():
        message = f"{directory}: stack and module directories must not be symlinks"
        raise StacksError(message)
    if not path.is_dir():
        return []
    files = sorted({file for pattern in CONFIG_PATTERNS for file in path.glob(pattern)})
    sources: list[str] = []
    for file in files:
        where = f"{directory}/{file.name}"
        if file.is_symlink():
            message = f"{where}: stack and module files must not be symlinks"
            raise StacksError(message)
        if not file.is_file():
            continue
        config = load_config(file, where)
        for (name,), body in config.blocks("module", 1):
            source = config.literal(body.get("source"))
            if source is None:
                message = f"{where}: module {name}: source must be a literal string"
                raise StacksError(message)
            if source.startswith(LOCAL_PREFIXES):
                sources.append(source)
    return sources


def join_path(base: str, relative: str) -> str | None:
    """Resolve ``relative`` against the repo-relative ``base``.

    Returns ``None`` if the result leaves the repository.
    """
    parts: list[str] = []
    for part in (*PurePosixPath(base).parts, *PurePosixPath(relative).parts):
        if part != "..":
            parts.append(part)
        elif parts:
            parts.pop()
        else:
            return None
    return "/".join(parts)
