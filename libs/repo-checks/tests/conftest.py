"""Shared pytest-bdd steps for the repo-checks features."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, then, when

from repo_checks.cli import CHECKS, main

if TYPE_CHECKING:
    from repo_checks.findings import Finding

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Workspace:
    """A repository under test and the results of running checks against it."""

    root: Path
    findings: list[Finding] = field(default_factory=list)
    exit_code: int | None = None
    output: str = ""

    def rendered(self) -> list[str]:
        return [finding.render(self.root) for finding in self.findings]


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(root=tmp_path)


@given(parsers.parse('a file "{path}" containing:'))
def file_containing(workspace: Workspace, path: str, docstring: str) -> None:
    target = workspace.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{docstring}\n", encoding="utf-8")


@given(parsers.parse('an empty directory "{path}"'))
def empty_directory(workspace: Workspace, path: str) -> None:
    (workspace.root / path).mkdir(parents=True, exist_ok=True)


@given("the gcp-agent-factory repository")
def the_real_repository(workspace: Workspace) -> None:
    workspace.root = REPO_ROOT


@when(parsers.parse('I run the "{check}" check'))
def run_check(workspace: Workspace, check: str) -> None:
    workspace.findings = CHECKS[check](workspace.root)


@when(parsers.parse('I run repo-checks with "{check}"'))
def run_cli(workspace: Workspace, check: str, capsys: pytest.CaptureFixture[str]) -> None:
    workspace.exit_code = main([check, "--root", str(workspace.root)])
    workspace.output = capsys.readouterr().out


@then("no findings are reported")
def no_findings(workspace: Workspace) -> None:
    assert workspace.rendered() == []


@then(parsers.parse('no findings are reported for "{path}"'))
def no_findings_for(workspace: Workspace, path: str) -> None:
    rendered = workspace.rendered()
    assert not [line for line in rendered if line.startswith(path)], rendered


@then(parsers.parse('a finding for "{path}" mentions "{text}"'))
def finding_mentions(workspace: Workspace, path: str, text: str) -> None:
    rendered = workspace.rendered()
    assert any(line.startswith(path) and text in line for line in rendered), rendered


@then(parsers.parse("exactly {count:d} finding is reported"))
@then(parsers.parse("exactly {count:d} findings are reported"))
def finding_count(workspace: Workspace, count: int) -> None:
    assert len(workspace.findings) == count, workspace.rendered()


@then(parsers.parse("repo-checks exits with code {code:d}"))
def exit_code(workspace: Workspace, code: int) -> None:
    assert workspace.exit_code == code, workspace.output
