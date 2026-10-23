"""Third-party CI and hook code is pinned to commit SHAs (REQ-REPO-005)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from repo_checks.findings import Finding

CHECK = "pins"
WORKFLOWS_DIR = Path(".github") / "workflows"
ACTIONS_DIR = Path(".github") / "actions"
PRE_COMMIT_CONFIG = Path(".pre-commit-config.yaml")
USES = re.compile(r"""^\s*(?:-\s*)?uses:\s*["']?(?P<ref>[^"'\s#]+)""")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA_PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
DOCKER_PINNED = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
UNPINNED_REVISION_REPOS = frozenset({"local", "meta"})


def _workflow_files(root: Path) -> list[Path]:
    workflows = root / WORKFLOWS_DIR
    actions = root / ACTIONS_DIR
    files = sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []
    files += sorted(actions.rglob("action.y*ml")) if actions.is_dir() else []
    return files


def _check_uses(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = USES.match(line)
        if match is None:
            continue
        ref = match.group("ref")
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DOCKER_PINNED.match(ref):
                message = f"{ref} must be pinned by @sha256 digest"
                findings.append(Finding(CHECK, path, message, number))
            continue
        if not SHA_PINNED.match(ref):
            message = f"{ref} must be pinned to a full 40-character commit SHA"
            findings.append(Finding(CHECK, path, message, number))
    return findings


def _check_pre_commit(path: Path) -> list[Finding]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return [Finding(CHECK, path, "invalid YAML")]
    repos = data.get("repos", []) if isinstance(data, dict) else []
    findings: list[Finding] = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        url = repo.get("repo")
        if url in UNPINNED_REVISION_REPOS:
            continue
        rev = repo.get("rev")
        if not isinstance(rev, str) or not FULL_SHA.match(rev):
            message = f"{url}: rev {rev!r} must be a full 40-character commit SHA"
            findings.append(Finding(CHECK, path, message))
    return findings


def check_pins(root: Path) -> list[Finding]:
    """Workflow ``uses:`` references and pre-commit ``rev:`` values are immutable SHAs."""
    findings = [finding for path in _workflow_files(root) for finding in _check_uses(path)]
    pre_commit = root / PRE_COMMIT_CONFIG
    if pre_commit.is_file():
        findings.extend(_check_pre_commit(pre_commit))
    return findings
