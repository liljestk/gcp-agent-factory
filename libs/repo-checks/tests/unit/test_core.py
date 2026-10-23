from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from repo_checks.cli import main
from repo_checks.files import iter_files
from repo_checks.findings import Finding
from repo_checks.frontmatter import parse_frontmatter

if TYPE_CHECKING:
    from pathlib import Path


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestFinding:
    def test_render_outside_root_uses_full_path(self, tmp_path: Path) -> None:
        outside = tmp_path / "elsewhere" / "file.md"
        finding = Finding("demo", outside, "broken", line=7)
        assert finding.render(tmp_path / "repo") == f"{outside.as_posix()}:7: [demo] broken"

    def test_render_relative_without_line(self, tmp_path: Path) -> None:
        finding = Finding("demo", tmp_path / "a" / "b.md", "broken")
        assert finding.render(tmp_path) == "a/b.md: [demo] broken"


class TestIterFiles:
    def test_skips_ignored_directories_and_filters_suffixes(self, tmp_path: Path) -> None:
        write(tmp_path, "src/keep.py", "")
        write(tmp_path, "src/skip.txt", "")
        write(tmp_path, ".venv/lib/site.py", "")
        write(tmp_path, "node_modules/pkg/index.py", "")
        found = [path.relative_to(tmp_path).as_posix() for path in iter_files(tmp_path, (".py",))]
        assert found == ["src/keep.py"]


class TestParseFrontmatter:
    @pytest.mark.parametrize(
        "text",
        [
            "",
            "# no front matter\n",
            "---\nname: unclosed\n",
            "---\nname: [unbalanced\n---\n",
            "---\n- a\n- list\n---\n",
        ],
        ids=["empty", "absent", "unclosed", "invalid-yaml", "not-a-mapping"],
    )
    def test_returns_none_for_unusable_front_matter(self, text: str) -> None:
        assert parse_frontmatter(text) is None

    def test_parses_mapping_with_string_keys(self) -> None:
        assert parse_frontmatter("---\nname: x\n1: one\n---\nbody\n") == {"name": "x", "1": "one"}


class TestCli:
    def test_single_check_with_findings_exits_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / ".claude" / "skills" / "orphan").mkdir(parents=True)
        assert main(["skills", "--root", str(tmp_path)]) == 1
        output = capsys.readouterr().out
        assert ".claude/skills/orphan: [skills] missing SKILL.md" in output
        assert "repo-checks: 1 finding(s) in skills" in output

    def test_clean_repository_exits_0(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(["all", "--root", str(tmp_path)]) == 0
        assert "passed" in capsys.readouterr().out

    def test_unknown_check_is_a_usage_error(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["nope"])
        assert excinfo.value.code == 2
