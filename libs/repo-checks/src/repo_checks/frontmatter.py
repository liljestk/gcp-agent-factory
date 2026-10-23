"""YAML front matter parsing for Markdown files."""

from __future__ import annotations

import yaml

_DELIMITER = "---"


def _closing_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == _DELIMITER:
            return index
    return None


def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Return the front matter mapping of a Markdown document.

    Args:
        text: Full document text.

    Returns:
        The parsed mapping, or ``None`` when the document has no front matter, the block is
        not closed, the YAML is invalid, or the YAML is not a mapping.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIMITER:
        return None
    end = _closing_index(lines)
    if end is None:
        return None
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return {str(key): value for key, value in data.items()}
