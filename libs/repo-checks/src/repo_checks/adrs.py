"""Checks for Architecture Decision Records (REQ-REPO-002)."""

from __future__ import annotations

import re
from pathlib import Path

from repo_checks.findings import Finding
from repo_checks.frontmatter import parse_frontmatter

CHECK = "adrs"
ADR_DIR = Path("docs") / "adr"
INDEX_NAME = "README.md"
TEMPLATE_NUMBER = "0000"
FILENAME_PATTERN = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
STATUS_PATTERN = re.compile(r"^(proposed|accepted|rejected|deprecated|superseded by ADR-\d{4})$")
TITLE_PATTERN = re.compile(r"^# ADR-(\d{4}): \S")


def _check_content(path: Path, number: str) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    meta = parse_frontmatter(text)
    status = meta.get("status") if meta is not None else None
    if not isinstance(status, str) or not STATUS_PATTERN.match(status):
        findings.append(Finding(CHECK, path, f"invalid status {status!r}"))
    title = next((line for line in text.splitlines() if line.startswith("# ")), "")
    title_match = TITLE_PATTERN.match(title)
    if title_match is None or title_match.group(1) != number:
        findings.append(Finding(CHECK, path, f"first heading must be '# ADR-{number}: <title>'"))
    return findings


def check_adrs(root: Path) -> list[Finding]:
    """ADRs have valid names, status and titles, unique numbers, and appear in the index."""
    adr_dir = root / ADR_DIR
    if not adr_dir.is_dir():
        return []
    index_path = adr_dir / INDEX_NAME
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    index_label = (ADR_DIR / INDEX_NAME).as_posix()
    findings: list[Finding] = []
    seen: dict[str, Path] = {}
    for path in sorted(adr_dir.glob("*.md")):
        if path.name == INDEX_NAME:
            continue
        match = FILENAME_PATTERN.match(path.name)
        if match is None:
            findings.append(Finding(CHECK, path, "file name must be NNNN-kebab-case-title.md"))
            continue
        number = match.group(1)
        if number == TEMPLATE_NUMBER:
            continue
        if number in seen:
            findings.append(
                Finding(CHECK, path, f"duplicate ADR number {number} (also {seen[number].name})"),
            )
        seen[number] = path
        findings.extend(_check_content(path, number))
        if f"({path.name})" not in index_text:
            findings.append(Finding(CHECK, path, f"not linked from {index_label}"))
    return findings
