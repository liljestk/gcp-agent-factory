from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stacks.changes import changed_paths
from stacks.errors import StacksError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def commit_all(root: Path, git: Callable[..., str], message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path, git: Callable[..., str]) -> tuple[Path, str]:
    (tmp_path / "stacks" / "network").mkdir(parents=True)
    (tmp_path / "stacks" / "network" / "main.tf").write_text("# network\n", encoding="utf-8")
    (tmp_path / "docs.md").write_text("docs\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    return tmp_path, commit_all(tmp_path, git, "base")


class TestChangedPaths:
    def test_lists_both_sides_of_a_rename(
        self,
        repository: tuple[Path, str],
        git: Callable[..., str],
    ) -> None:
        root, base = repository
        (root / "archive").mkdir()
        git(root, "mv", "stacks/network/main.tf", "archive/main.tf")
        commit_all(root, git, "move")
        assert sorted(changed_paths(root, base)) == ["archive/main.tf", "stacks/network/main.tf"]

    def test_returns_non_ascii_names_unquoted(
        self,
        repository: tuple[Path, str],
        git: Callable[..., str],
    ) -> None:
        root, base = repository
        (root / "stacks" / "network" / "brandvägg.tf").write_text("# fw\n", encoding="utf-8")
        commit_all(root, git, "add")
        assert changed_paths(root, base) == ["stacks/network/brandvägg.tf"]

    def test_no_change_is_an_empty_list(self, repository: tuple[Path, str]) -> None:
        root, base = repository
        assert changed_paths(root, base) == []

    @pytest.mark.parametrize("base", ["main", "--output=x", "HEAD~1", "abc", ""])
    def test_rejects_anything_but_a_commit_sha(
        self,
        repository: tuple[Path, str],
        base: str,
    ) -> None:
        with pytest.raises(StacksError, match="--base must be a commit SHA"):
            changed_paths(repository[0], base)

    def test_fails_closed_when_git_fails(self, repository: tuple[Path, str]) -> None:
        with pytest.raises(StacksError, match=r"git diff 0{40}\.\.\.HEAD failed"):
            changed_paths(repository[0], "0" * 40)

    def test_fails_closed_without_git(
        self,
        repository: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("stacks.changes.shutil.which", lambda _name: None)
        with pytest.raises(StacksError, match="git is not on PATH"):
            changed_paths(*repository)
