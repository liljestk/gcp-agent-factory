"""Shared pytest-bdd steps and fixtures for the stacks tests."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pytest_bdd import given, parsers, then, when

from stacks.catalog import CatalogError, load_catalog
from stacks.changes import changed_paths
from stacks.errors import StacksError
from stacks.matrix import Matrix, compute

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from stacks.catalog import Catalog

TIERS = ["canary", "foundation", "network"]
ALL_STACKS_PATHS = ["mise.toml", "platforms/stacks.yaml", ".github/workflows/", ".github/actions/"]
GIT = shutil.which("git")


def run_git(root: Path, *args: str) -> str:
    """Run git in ``root`` with a throwaway identity and no signing or line-ending rewrites."""
    assert GIT is not None, "these tests need git on PATH"
    options = ["-c", "user.name=test", "-c", "user.email=test@example.com"]
    options += ["-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]
    # Test helper: a fixed git command line built from literals in the tests.
    result = subprocess.run(  # noqa: S603
        [GIT, *options, *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def git() -> Callable[..., str]:
    return run_git


@dataclass
class Repo:
    """A repository under test: its stack catalog and the jobs computed from it."""

    root: Path
    catalog: dict[str, Any] = field(default_factory=dict)
    base: str = ""
    matrix: Matrix | None = None
    error: StacksError | None = None

    def load(self) -> Catalog:
        path = self.root / "platforms" / "stacks.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.catalog, sort_keys=False), encoding="utf-8")
        return load_catalog(path)

    def jobs(self) -> Matrix:
        assert self.matrix is not None, f"no jobs were computed: {self.error}"
        return self.matrix

    def write(self, relative: str, text: str = "") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def compute(self, changed: list[str] | None) -> None:
        try:
            self.matrix = compute(self.load(), self.root, changed)
        except StacksError as error:
            self.error = error


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(root=tmp_path)


def _split(text: str) -> list[str]:
    return [item.strip() for item in text.split(",")]


def _module_block(name: str, source: str) -> str:
    return f'module "{name}" {{\n  source = {source}\n}}\n'


@given("the stack catalog:")
def stack_catalog(repo: Repo, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    stacks: dict[str, dict[str, Any]] = {}
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        entry: dict[str, Any] = {"path": f"stacks/{cells['stack']}"}
        instances = _split(cells["instances"])
        if instances[0] in ("trust-root", "shared"):
            entry["scope"] = instances[0]
        else:
            entry["envs"] = instances
        if instances[0] == "shared":
            entry["environment"] = "foundation"
        if cells["tier"]:
            entry["tier"] = cells["tier"]
        entry["plan"] = cells["plan"]
        entry["apply"] = cells["apply"]
        stacks[cells["stack"]] = entry
    repo.catalog = {"tiers": TIERS, "all-stacks-paths": ALL_STACKS_PATHS, "stacks": stacks}


@given(
    parsers.re(
        r'the stack "(?P<stack>[^"]+)" uses module "(?P<module>[^"]+)", '
        r'which uses module "(?P<inner>[^"]+)"',
    ),
)
def stack_uses_nested_module(repo: Repo, stack: str, module: str, inner: str) -> None:
    repo.write(f"stacks/{stack}/main.tf", _module_block(module, f'"../../modules/{module}"'))
    repo.write(f"modules/{module}/main.tf", _module_block(inner, f'"../{inner}"'))
    repo.write(f"modules/{inner}/main.tf")


@given(parsers.re(r'the stack "(?P<stack>[^"]+)" uses module "(?P<module>[^"]+)"$'))
def stack_uses_module(repo: Repo, stack: str, module: str) -> None:
    repo.write(f"stacks/{stack}/main.tf", _module_block(module, f'"../../modules/{module}"'))
    repo.write(f"modules/{module}/main.tf")


@given(
    parsers.parse(
        'the stack "{stack}" also uses a module with the source expression "{expression}"',
    ),
)
def stack_uses_expression(repo: Repo, stack: str, expression: str) -> None:
    repo.write(f"stacks/{stack}/dynamic.tf", _module_block("dynamic", expression))


@given(parsers.parse('the stack "{stack}" uses the directory of stack "{other}" as a module'))
def stack_uses_stack(repo: Repo, stack: str, other: str) -> None:
    repo.write(f"stacks/{stack}/main.tf", _module_block("borrowed", f'"../{other}"'))


@given(parsers.parse('the catalog says CI applies the stack "{stack}"'))
def ci_applies(repo: Repo, stack: str) -> None:
    repo.catalog["stacks"][stack]["apply"] = "ci"


@given("the repository is committed")
def committed(repo: Repo) -> None:
    repo.load()
    run_git(repo.root, "init", "-q")
    run_git(repo.root, "add", "-A")
    run_git(repo.root, "commit", "-q", "-m", "base")
    repo.base = run_git(repo.root, "rev-parse", "HEAD")


@when(parsers.parse('a commit moves "{source}" to "{target}"'))
def commit_move(repo: Repo, source: str, target: str) -> None:
    (repo.root / target).parent.mkdir(parents=True, exist_ok=True)
    run_git(repo.root, "mv", source, target)
    run_git(repo.root, "commit", "-q", "-m", "move")


@when(parsers.parse('a commit adds "{path}"'))
def commit_add(repo: Repo, path: str) -> None:
    repo.write(path, "# added\n")
    run_git(repo.root, "add", "-A")
    run_git(repo.root, "commit", "-q", "-m", "add")


@when(parsers.parse('the affected stacks are computed for a change to "{path}"'))
def compute_for_change(repo: Repo, path: str) -> None:
    repo.compute([path])


@when("the jobs are computed from git since the first commit")
def compute_from_git(repo: Repo) -> None:
    repo.compute(changed_paths(repo.root, repo.base))


@when("the jobs are computed for every stack")
def compute_for_all(repo: Repo) -> None:
    repo.compute(None)


@when("the catalog is loaded")
def load(repo: Repo) -> None:
    try:
        repo.load()
    except CatalogError as error:
        repo.error = error


@then(parsers.parse('the plan jobs are "{jobs}"'))
def plan_jobs_are(repo: Repo, jobs: str) -> None:
    assert [instance.job_id for instance in repo.jobs().plan] == _split(jobs)


@then(parsers.parse('the plan jobs include "{job}"'))
def plan_jobs_include(repo: Repo, job: str) -> None:
    assert job in [instance.job_id for instance in repo.jobs().plan]


@then(parsers.parse('the apply groups with jobs are "{groups}"'))
def apply_groups_with_jobs(repo: Repo, groups: str) -> None:
    assert [group for group, jobs in repo.jobs().apply.items() if jobs] == _split(groups)


@then(parsers.parse('the apply groups in order are "{groups}"'))
def apply_groups_in_order(repo: Repo, groups: str) -> None:
    assert list(repo.jobs().apply) == _split(groups)


@then("nothing is planned or applied")
def nothing(repo: Repo) -> None:
    jobs = repo.jobs()
    assert jobs.plan == ()
    assert all(not instances for instances in jobs.apply.values())


@then(parsers.parse('no apply job exists for "{first}" or "{second}"'))
def no_apply_for(repo: Repo, first: str, second: str) -> None:
    applied = {instance.stack for instances in repo.jobs().apply.values() for instance in instances}
    assert applied.isdisjoint({first, second}), applied


@then(parsers.parse('it is rejected because "{reason}"'))
@then(parsers.parse('the run fails because "{reason}"'))
def rejected(repo: Repo, reason: str) -> None:
    assert repo.error is not None, "the catalog and graph were accepted"
    assert reason in str(repo.error)
