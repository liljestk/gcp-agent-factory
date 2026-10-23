"""Command-line entry point: ``repo-checks <check|all> [--root PATH]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from repo_checks.adrs import check_adrs
from repo_checks.pins import check_pins
from repo_checks.pragmas import check_pragmas
from repo_checks.skills import check_skills, check_subagents
from repo_checks.traceability import check_traceability

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from repo_checks.findings import Finding

CHECKS: Final[dict[str, Callable[[Path], list[Finding]]]] = {
    "skills": check_skills,
    "subagents": check_subagents,
    "adrs": check_adrs,
    "traceability": check_traceability,
    "pragmas": check_pragmas,
    "pins": check_pins,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected checks and return ``0`` when clean or ``1`` when findings exist."""
    parser = argparse.ArgumentParser(
        prog="repo-checks",
        description="Check gcp-agent-factory repository conventions.",
    )
    parser.add_argument("check", choices=[*CHECKS, "all"], help="check to run, or 'all'")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    args = parser.parse_args(argv)
    root: Path = args.root.resolve()
    names = list(CHECKS) if args.check == "all" else [args.check]
    findings = [finding for name in names for finding in CHECKS[name](root)]
    for finding in findings:
        sys.stdout.write(f"{finding.render(root)}\n")
    summary = ", ".join(names)
    if findings:
        sys.stdout.write(f"repo-checks: {len(findings)} finding(s) in {summary}\n")
        return 1
    sys.stdout.write(f"repo-checks: {summary} passed\n")
    return 0
