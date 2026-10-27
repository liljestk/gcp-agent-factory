"""Local module references between OpenTofu root modules and reusable modules.

The matrix is only as good as this graph, so it fails closed: a source it can't resolve to a
literal path inside the repository, a file it can't parse and any symlink raise ``StacksError``
instead of being skipped.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final

import hcl2
from lark.exceptions import LarkError

from stacks.errors import StacksError

if TYPE_CHECKING:
    from pathlib import Path

# Every file OpenTofu loads from a module directory.
SOURCE_PATTERNS: Final = ("*.tf", "*.tofu", "*.tf.json", "*.tofu.json")
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
            target = _join(current, source)
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
    files = sorted({file for pattern in SOURCE_PATTERNS for file in path.glob(pattern)})
    sources: list[str] = []
    for file in files:
        where = f"{directory}/{file.name}"
        if file.is_symlink():
            message = f"{where}: stack and module files must not be symlinks"
            raise StacksError(message)
        if file.is_file():
            text = _read(file, where)
            found = (
                _json_sources(text, where) if file.suffix == ".json" else _hcl_sources(text, where)
            )
            sources.extend(source for source in found if source.startswith(LOCAL_PREFIXES))
    return sources


def _read(file: Path, where: str) -> str:
    try:
        return file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        message = f"{where}: can't be read ({error})"
        raise StacksError(message) from error


def _hcl_sources(text: str, where: str) -> list[str]:
    try:
        document = hcl2.loads(text)
    except LarkError as error:
        message = f"{where}: isn't valid HCL"
        raise StacksError(message) from error
    return [
        _hcl_literal(body.get("source", ""), f"{where}: module {name}")
        for block in document.get("module", [])
        for name, body in block.items()
    ]


def _hcl_literal(value: object, where: str) -> str:
    """python-hcl2 returns string literals with their quotes and expressions without."""
    text = str(value)
    if len(text) > 1 and text.startswith('"') and text.endswith('"') and "${" not in text:
        return text[1:-1]
    message = f"{where}: source {text} must be a literal string the pipeline can follow"
    raise StacksError(message)


def _json_sources(text: str, where: str) -> list[str]:
    try:
        document = json.loads(text)
        section = document.get("module", {})
        entries = section if isinstance(section, list) else [section]
        return [
            _json_literal(body.get("source", ""), f"{where}: module {name}")
            for entry in entries
            for name, bodies in entry.items()
            for body in (bodies if isinstance(bodies, list) else [bodies])
        ]
    except (json.JSONDecodeError, AttributeError) as error:
        message = f"{where}: isn't a valid OpenTofu JSON configuration"
        raise StacksError(message) from error


def _json_literal(value: object, where: str) -> str:
    if isinstance(value, str) and value and "${" not in value:
        return value
    message = f"{where}: source {value!r} must be a literal string the pipeline can follow"
    raise StacksError(message)


def _join(base: str, relative: str) -> str | None:
    """Resolve ``relative`` against ``base``; ``None`` if the result leaves the repository."""
    parts: list[str] = []
    for part in (*PurePosixPath(base).parts, *PurePosixPath(relative).parts):
        if part != "..":
            parts.append(part)
        elif parts:
            parts.pop()
        else:
            return None
    return "/".join(parts)
