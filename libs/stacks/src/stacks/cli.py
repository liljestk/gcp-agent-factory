"""Command-line entry point: ``stacks <matrix|validate> [--root PATH] [--catalog PATH]``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from stacks.catalog import CATALOG_PATH, load_catalog
from stacks.changes import changed_paths
from stacks.errors import StacksError
from stacks.matrix import boundary_problems, compute
from stacks.modules import local_modules

if TYPE_CHECKING:
    from collections.abc import Sequence

    from stacks.catalog import Catalog


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return ``0`` on success or ``1`` on any error or finding."""
    parser = argparse.ArgumentParser(
        prog="stacks",
        description="Plan/apply matrix for the gcp-agent-factory OpenTofu stacks (spec 002).",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    matrix = commands.add_parser("matrix", help="print the CI jobs as one line of JSON")
    scope = matrix.add_mutually_exclusive_group(required=True)
    scope.add_argument("--base", help="commit SHA to diff HEAD against (git diff BASE...HEAD)")
    scope.add_argument("--all", action="store_true", help="every stack (drift runs)")
    validate = commands.add_parser(
        "validate",
        help="check the catalog, every stack path and the module graph",
    )
    for command in (matrix, validate):
        command.add_argument(
            "--root",
            type=Path,
            default=Path.cwd(),
            help="repository root (default: current directory)",
        )
        command.add_argument(
            "--catalog",
            type=Path,
            help=f"catalog file (default: <root>/{CATALOG_PATH.as_posix()})",
        )
    args = parser.parse_args(argv)
    root: Path = args.root.resolve()
    try:
        catalog = load_catalog(args.catalog or root / CATALOG_PATH)
        if args.command == "validate":
            return _validate(catalog, root)
        changed = None if args.all else changed_paths(root, args.base)
        document = compute(catalog, root, changed).to_json()
    except StacksError as error:
        sys.stderr.write(f"stacks: {error}\n")
        return 1
    sys.stdout.write(f"{json.dumps(document, separators=(',', ':'))}\n")
    return 0


def _validate(catalog: Catalog, root: Path) -> int:
    findings = [
        f"{stack.path}: [stacks] stack {stack.name!r} has no directory"
        for stack in catalog.stacks
        if not (root / stack.path).is_dir()
    ]
    modules = {stack.name: local_modules(root, stack.path) for stack in catalog.stacks}
    findings += [
        f"{CATALOG_PATH.as_posix()}: [stacks] {problem}"
        for problem in boundary_problems(catalog, modules)
    ]
    for finding in findings:
        sys.stdout.write(f"{finding}\n")
    if findings:
        return 1
    sys.stdout.write(f"stacks: catalog valid ({len(catalog.stacks)} stacks)\n")
    return 0
