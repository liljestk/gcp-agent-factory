"""Read OpenTofu configuration files, in HCL or JSON syntax, into one shape.

The stack matrix and ``repo-checks`` both read configuration through this module, so they
can't disagree about what a file contains. Anything unexpected raises ``StacksError``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import hcl2
from lark.exceptions import LarkError

from stacks.errors import StacksError

if TYPE_CHECKING:
    from pathlib import Path

# Every file OpenTofu loads from a module directory.
CONFIG_PATTERNS: Final = ("*.tf", "*.tofu", "*.tf.json", "*.tofu.json")
CONFIG_SUFFIXES: Final = (".tf", ".tofu", ".tf.json", ".tofu.json")
# A `.tofu` file shadows the `.tf` file of the same name; the JSON forms pair up the same way.
_SHADOWED: Final = ((".tf", ".tofu"), (".tf.json", ".tofu.json"))
_BLOCK_MARKER: Final = "__is_block__"

Block = tuple[tuple[str, ...], dict[str, object]]


def config_paths(directory: Path) -> list[Path]:
    """Return the configuration files OpenTofu loads from ``directory``, in name order.

    ``X.tofu`` shadows ``X.tf`` and ``X.tofu.json`` shadows ``X.tf.json``, as in OpenTofu.
    """
    files = sorted(
        {file for pattern in CONFIG_PATTERNS for file in directory.glob(pattern) if file.is_file()},
    )
    names = {file.name for file in files}
    return [
        file
        for file in files
        if not any(
            file.name.endswith(old) and f"{file.name.removesuffix(old)}{new}" in names
            for old, new in _SHADOWED
        )
    ]


def contains_key(node: object, key: str) -> bool:
    """Whether ``key`` appears in ``node`` or in any mapping nested in it."""
    if isinstance(node, dict):
        return key in node or any(contains_key(value, key) for value in node.values())
    if isinstance(node, list):
        return any(contains_key(item, key) for item in node)
    return False


def is_override(name: str) -> bool:
    """Whether ``name`` is an override file (``override.tf``, ``x_override.tofu``, …)."""
    stem = next(
        (name.removesuffix(suffix) for suffix in CONFIG_SUFFIXES if name.endswith(suffix)), ""
    )
    return stem == "override" or stem.endswith("_override")


@dataclass(frozen=True, slots=True)
class ConfigFile:
    """One parsed configuration file.

    Attributes:
        where: Repo-relative path, used in messages.
        text: The raw file content.
        document: The parsed top level.
        json_syntax: ``True`` for ``*.tf.json`` and ``*.tofu.json`` files.
    """

    where: str
    text: str
    document: dict[str, object]
    json_syntax: bool

    def blocks(self, kind: str, labels: int) -> list[Block]:
        """Return every top-level ``kind`` block with ``labels`` labels as ``(labels, body)``."""
        return self.blocks_in(self.document, kind, labels)

    def blocks_in(self, container: dict[str, object], kind: str, labels: int) -> list[Block]:
        """Return every ``kind`` block nested directly in ``container`` as ``(labels, body)``.

        Raises:
            StacksError: The blocks don't have the shape OpenTofu configuration has.
        """
        section = container.get(kind)
        if section is None:
            return []
        if self.json_syntax:
            return self._json_blocks(section, kind, labels, ())
        if not isinstance(section, list):
            raise self._malformed(kind)
        return [block for item in section for block in self._hcl_blocks(item, kind, labels, ())]

    def literal(self, value: object) -> str | None:
        """Return the value of a string literal, or ``None`` for anything else.

        python-hcl2 leaves HCL escapes undecoded, so an HCL string with a backslash or a ``%{``
        template directive counts as an expression: what it means can't be read safely.
        """
        if not isinstance(value, str) or "${" in value:
            return None
        if self.json_syntax:
            return value
        if (
            len(value) > 1
            and value.startswith('"')
            and value.endswith('"')
            and "\\" not in value
            and "%{" not in value
        ):
            return value[1:-1]
        return None

    def line_of(self, pattern: str) -> int | None:
        """Return the 1-based line of the first match of regex ``pattern``, if any."""
        match = re.search(pattern, self.text)
        return None if match is None else self.text.count("\n", 0, match.start()) + 1

    def _hcl_blocks(
        self, node: object, kind: str, depth: int, labels: tuple[str, ...]
    ) -> list[Block]:
        if not isinstance(node, dict):
            raise self._malformed(kind)
        body = {str(key): value for key, value in node.items() if key != _BLOCK_MARKER}
        if depth == 0:
            return [(labels, body)]
        if any("\\" in key for key in body):
            message = f"{self.where}: escape sequences aren't allowed in {kind} block labels"
            raise StacksError(message)
        return [
            block
            for key, child in body.items()
            for block in self._hcl_blocks(child, kind, depth - 1, (*labels, key.strip('"')))
        ]

    def _json_blocks(
        self, node: object, kind: str, depth: int, labels: tuple[str, ...]
    ) -> list[Block]:
        if isinstance(node, list):
            return [
                block for item in node for block in self._json_blocks(item, kind, depth, labels)
            ]
        if not isinstance(node, dict):
            raise self._malformed(kind)
        body = {str(key): value for key, value in node.items()}
        if depth == 0:
            return [(labels, body)]
        return [
            block
            for key, child in body.items()
            for block in self._json_blocks(child, kind, depth - 1, (*labels, key))
        ]

    def _malformed(self, kind: str) -> StacksError:
        return StacksError(f"{self.where}: {kind} blocks have an unexpected shape")


def load_config(path: Path, where: str) -> ConfigFile:
    """Read and parse one configuration file; ``where`` names it in messages.

    Raises:
        StacksError: The file can't be read or isn't valid HCL or OpenTofu JSON.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        message = f"{where}: can't be read ({error})"
        raise StacksError(message) from error
    if path.name.endswith(".json"):
        try:
            document: object = json.loads(text)
        except json.JSONDecodeError as error:
            message = f"{where}: isn't a valid OpenTofu JSON configuration"
            raise StacksError(message) from error
        if not isinstance(document, dict):
            message = f"{where}: isn't a valid OpenTofu JSON configuration"
            raise StacksError(message)
        items = {str(key): value for key, value in document.items()}
        return ConfigFile(where=where, text=text, document=items, json_syntax=True)
    try:
        parsed = hcl2.loads(text)
    except LarkError as error:
        message = f"{where}: isn't valid HCL"
        raise StacksError(message) from error
    items = {str(key): value for key, value in parsed.items()}
    return ConfigFile(where=where, text=text, document=items, json_syntax=False)
