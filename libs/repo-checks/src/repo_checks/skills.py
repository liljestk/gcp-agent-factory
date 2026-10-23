"""Checks for Claude skills and subagents (REQ-REPO-001)."""

from __future__ import annotations

import re
from pathlib import Path

from repo_checks.findings import Finding
from repo_checks.frontmatter import parse_frontmatter

SKILLS_CHECK = "skills"
SUBAGENTS_CHECK = "subagents"
SKILLS_DIR = Path(".claude") / "skills"
SUBAGENTS_DIR = Path(".claude") / "agents"
MAX_DESCRIPTION_LENGTH = 1024
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64


def _check_metadata(check: str, path: Path, expected_name: str) -> list[Finding]:
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    if meta is None:
        return [Finding(check, path, "missing or invalid YAML front matter")]
    findings: list[Finding] = []
    name = meta.get("name")
    if name != expected_name:
        findings.append(Finding(check, path, f"name {name!r} must equal {expected_name!r}"))
    elif not NAME_PATTERN.match(expected_name) or len(expected_name) > MAX_NAME_LENGTH:
        findings.append(
            Finding(check, path, "name must be lowercase letters, digits and hyphens (max 64)"),
        )
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(Finding(check, path, "description is required"))
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        findings.append(
            Finding(check, path, f"description exceeds {MAX_DESCRIPTION_LENGTH} characters"),
        )
    return findings


def check_skills(root: Path) -> list[Finding]:
    """Every ``.claude/skills/<dir>/`` has a ``SKILL.md`` with valid front matter."""
    base = root / SKILLS_DIR
    if not base.is_dir():
        return []
    findings: list[Finding] = []
    for skill_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            findings.append(Finding(SKILLS_CHECK, skill_dir, "missing SKILL.md"))
            continue
        findings.extend(_check_metadata(SKILLS_CHECK, skill_file, skill_dir.name))
    return findings


def check_subagents(root: Path) -> list[Finding]:
    """Every ``.claude/agents/<name>.md`` has front matter with ``name`` and ``description``."""
    base = root / SUBAGENTS_DIR
    if not base.is_dir():
        return []
    return [
        finding
        for path in sorted(base.glob("*.md"))
        for finding in _check_metadata(SUBAGENTS_CHECK, path, path.stem)
    ]
