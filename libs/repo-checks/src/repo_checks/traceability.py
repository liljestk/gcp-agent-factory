"""Requirement-to-test traceability (REQ-REPO-003).

Requirements are Markdown headings ``REQ-<AREA>-<NNN>`` in ``specs/*/requirements.md``.
References are ``@REQ-…`` tags in ``.feature`` files and ``# covers: REQ-…`` comments in
``*.tftest.hcl`` files. Text inside Gherkin docstrings and Markdown code fences is ignored, so
examples never count as definitions or references.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from repo_checks.files import iter_files
from repo_checks.findings import Finding

if TYPE_CHECKING:
    from collections.abc import Iterator

CHECK = "traceability"
SPECS_DIR = Path("specs")
REQUIREMENTS_FILE = "requirements.md"
_ID = r"REQ-[A-Z][A-Z0-9]*-\d{3}"
REQUIREMENT_ID = re.compile(_ID)
DEFINITION = re.compile(rf"^#{{2,6}}\s+({_ID})\b")
FEATURE_TAG = re.compile(rf"@({_ID})\b")
COVERS_COMMENT = re.compile(r"#\s*covers:\s*(?P<ids>.+)$")
_FENCES = ('"""', "```")


@dataclass(frozen=True, slots=True)
class Location:
    """Where a requirement is defined or referenced."""

    path: Path
    line: int


def _lines_outside_fences(path: Path) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, line)`` pairs that are not inside a docstring or code fence."""
    open_fence: str | None = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        marker = next((fence for fence in _FENCES if stripped.startswith(fence)), None)
        if marker is not None and open_fence in (None, marker):
            open_fence = None if open_fence else marker
            continue
        if open_fence is None:
            yield number, line


def collect_requirements(root: Path) -> tuple[dict[str, Location], list[Finding]]:
    """Return requirement definitions and findings for duplicate definitions."""
    definitions: dict[str, Location] = {}
    findings: list[Finding] = []
    specs = root / SPECS_DIR
    if not specs.is_dir():
        return definitions, findings
    for spec_dir in sorted(specs.iterdir()):
        requirements = spec_dir / REQUIREMENTS_FILE
        if spec_dir.name.startswith("_") or not requirements.is_file():
            continue
        for number, line in _lines_outside_fences(requirements):
            match = DEFINITION.match(line)
            if match is None:
                continue
            requirement = match.group(1)
            if requirement in definitions:
                first = definitions[requirement]
                where = f"{first.path.relative_to(root).as_posix()}:{first.line}"
                findings.append(
                    Finding(
                        CHECK, requirements, f"{requirement} is already defined at {where}", number
                    ),
                )
            else:
                definitions[requirement] = Location(requirements, number)
    return definitions, findings


def collect_references(root: Path) -> dict[str, list[Location]]:
    """Return every requirement referenced by a feature tag or a tftest ``covers`` comment."""
    references: dict[str, list[Location]] = defaultdict(list)
    for path in iter_files(root, (".feature",)):
        for number, line in _lines_outside_fences(path):
            for requirement in FEATURE_TAG.findall(line):
                references[requirement].append(Location(path, number))
    for path in iter_files(root, (".tftest.hcl",)):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = COVERS_COMMENT.search(line)
            if match is None:
                continue
            for requirement in REQUIREMENT_ID.findall(match.group("ids")):
                references[requirement].append(Location(path, number))
    return dict(references)


def check_traceability(root: Path) -> list[Finding]:
    """Every requirement has a test, and every test references a defined requirement."""
    definitions, findings = collect_requirements(root)
    references = collect_references(root)
    for requirement, location in definitions.items():
        if requirement not in references:
            findings.append(
                Finding(
                    CHECK,
                    location.path,
                    f"{requirement} has no test (tag a scenario @{requirement} "
                    f"or add '# covers: {requirement}' to a tftest file)",
                    location.line,
                ),
            )
    for requirement, locations in sorted(references.items()):
        if requirement in definitions:
            continue
        findings.extend(
            Finding(
                CHECK,
                location.path,
                f"{requirement} is not defined in specs/*/{REQUIREMENTS_FILE}",
                location.line,
            )
            for location in locations
        )
    return findings
