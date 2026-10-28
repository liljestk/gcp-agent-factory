from __future__ import annotations

import json
from typing import TYPE_CHECKING

from stacks.cli import main

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

CATALOG = """\
tiers: [canary]
all-stacks-paths: [mise.toml]
stacks:
  bootstrap:
    path: stacks/bootstrap
    scope: trust-root
    apply: local
  ci-canary:
    path: stacks/ci-canary
    tier: canary
    envs: [dev, prod]
"""


def repository(root: Path, *directories: str) -> Path:
    catalog = root / "platforms" / "stacks.yaml"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(CATALOG, encoding="utf-8")
    for directory in directories:
        (root / directory).mkdir(parents=True)
    return catalog


class TestMatrix:
    def test_diffs_head_against_the_base_commit(
        self,
        tmp_path: Path,
        git: Callable[..., str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path, "stacks/ci-canary")
        git(tmp_path, "init", "-q")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
        base = git(tmp_path, "rev-parse", "HEAD")
        (tmp_path / "stacks" / "ci-canary" / "main.tf").write_text("# canary\n", encoding="utf-8")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "change")
        assert main(["matrix", "--base", base, "--root", str(tmp_path)]) == 0
        document = json.loads(capsys.readouterr().out)
        assert [job["id"] for job in document["plan"]] == ["ci-canary/dev", "ci-canary/prod"]
        assert list(document["apply"]) == ["canary/shared", "canary/dev", "canary/prod"]

    def test_all_plans_every_stack(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repository(tmp_path)
        assert main(["matrix", "--all", "--root", str(tmp_path)]) == 0
        plan = [job["id"] for job in json.loads(capsys.readouterr().out)["plan"]]
        assert plan == ["bootstrap/trust-root", "ci-canary/dev", "ci-canary/prod"]

    def test_explicit_catalog_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        catalog = repository(tmp_path / "repo")
        moved = tmp_path / "elsewhere.yaml"
        catalog.rename(moved)
        args = ["matrix", "--all", "--root", str(tmp_path / "repo"), "--catalog", str(moved)]
        assert main(args) == 0
        assert '"plan"' in capsys.readouterr().out

    def test_invalid_catalog_exits_1_on_stderr(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(["matrix", "--all", "--root", str(tmp_path)]) == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.startswith("stacks: ")
        assert "can't be read" in captured.err

    def test_a_failing_diff_exits_1_instead_of_planning_nothing(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path)
        assert main(["matrix", "--base", "0" * 40, "--root", str(tmp_path)]) == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "git diff" in captured.err


class TestValidate:
    def test_reports_stacks_without_a_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path, "stacks/bootstrap")
        assert main(["validate", "--root", str(tmp_path)]) == 1
        out = capsys.readouterr().out
        assert out == "stacks/ci-canary: [stacks] stack 'ci-canary' has no directory\n"

    def test_reports_stacks_that_use_another_stack(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path, "stacks/bootstrap", "stacks/ci-canary")
        (tmp_path / "stacks" / "ci-canary" / "main.tf").write_text(
            'module "b" {\n  source = "../bootstrap"\n}\n',
            encoding="utf-8",
        )
        assert main(["validate", "--root", str(tmp_path)]) == 1
        assert "which is inside stack 'bootstrap'" in capsys.readouterr().out

    def test_module_errors_exit_1_on_stderr(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path, "stacks/bootstrap", "stacks/ci-canary")
        (tmp_path / "stacks" / "ci-canary" / "main.tf").write_text("module {\n", encoding="utf-8")
        assert main(["validate", "--root", str(tmp_path)]) == 1
        assert "isn't valid HCL" in capsys.readouterr().err

    def test_passes_when_every_stack_exists(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repository(tmp_path, "stacks/bootstrap", "stacks/ci-canary")
        assert main(["validate", "--root", str(tmp_path)]) == 0
        assert capsys.readouterr().out == "stacks: catalog valid (2 stacks)\n"
