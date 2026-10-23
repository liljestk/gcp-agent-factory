from __future__ import annotations

from typing import TYPE_CHECKING

from repo_checks.adrs import check_adrs
from repo_checks.pins import check_pins
from repo_checks.skills import check_skills, check_subagents
from repo_checks.traceability import check_traceability

if TYPE_CHECKING:
    from pathlib import Path

    from repo_checks.findings import Finding


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def messages(findings: list[Finding]) -> list[str]:
    return [finding.message for finding in findings]


class TestMissingDirectories:
    def test_every_check_is_empty_on_an_empty_repository(self, tmp_path: Path) -> None:
        for check in (check_skills, check_subagents, check_adrs, check_traceability, check_pins):
            assert check(tmp_path) == []


class TestSkills:
    def test_invalid_name_format_is_rejected(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            ".claude/skills/Bad_Name/SKILL.md",
            "---\nname: Bad_Name\ndescription: x\n---\n",
        )
        assert messages(check_skills(tmp_path)) == [
            "name must be lowercase letters, digits and hyphens (max 64)",
        ]

    def test_overlong_description_is_rejected(self, tmp_path: Path) -> None:
        text = f"---\nname: long\ndescription: {'x' * 1025}\n---\n"
        write(tmp_path, ".claude/skills/long/SKILL.md", text)
        assert messages(check_skills(tmp_path)) == ["description exceeds 1024 characters"]

    def test_files_next_to_skill_folders_are_ignored(self, tmp_path: Path) -> None:
        write(tmp_path, ".claude/skills/README.md", "notes")
        assert check_skills(tmp_path) == []


class TestAdrs:
    def test_template_is_skipped_and_missing_index_is_reported(self, tmp_path: Path) -> None:
        write(tmp_path, "docs/adr/0000-template.md", "# ADR-NNNN: template\n")
        write(tmp_path, "docs/adr/0001-first.md", "---\nstatus: accepted\n---\n# ADR-0001: First\n")
        assert messages(check_adrs(tmp_path)) == ["not linked from docs/adr/README.md"]

    def test_missing_front_matter_and_title(self, tmp_path: Path) -> None:
        write(tmp_path, "docs/adr/README.md", "(0001-first.md)")
        write(tmp_path, "docs/adr/0001-first.md", "no front matter, no title\n")
        assert messages(check_adrs(tmp_path)) == [
            "invalid status None",
            "first heading must be '# ADR-0001: <title>'",
        ]


class TestTraceability:
    def test_fenced_examples_are_neither_definitions_nor_references(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "specs/001-x/requirements.md",
            "### REQ-X-001: Real\n\n```markdown\n### REQ-X-002: Example only\n```\n",
        )
        write(
            tmp_path,
            "tests/x.feature",
            '@REQ-X-001\nFeature: x\n  """\n  ```\n  @REQ-X-404\n  """\n',
        )
        assert check_traceability(tmp_path) == []

    def test_spec_folder_without_requirements_file_is_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "specs" / "002-empty").mkdir(parents=True)
        assert check_traceability(tmp_path) == []

    def test_covers_comment_can_list_several_requirements(self, tmp_path: Path) -> None:
        write(tmp_path, "specs/001-x/requirements.md", "## REQ-X-001: a\n## REQ-X-002: b\n")
        write(tmp_path, "modules/x/tests/x.tftest.hcl", "# covers: REQ-X-001, REQ-X-002\n")
        assert check_traceability(tmp_path) == []


class TestPins:
    def test_composite_actions_and_pinned_docker_images(self, tmp_path: Path) -> None:
        digest = "a" * 64
        write(
            tmp_path,
            ".github/actions/setup/action.yml",
            f"runs:\n  steps:\n    - uses: docker://alpine@sha256:{digest}\n"
            "    - uses: 'actions/setup-node@main'\n",
        )
        findings = check_pins(tmp_path)
        assert [(finding.line, finding.message) for finding in findings] == [
            (4, "actions/setup-node@main must be pinned to a full 40-character commit SHA"),
        ]

    def test_pre_commit_edge_cases(self, tmp_path: Path) -> None:
        write(tmp_path, ".pre-commit-config.yaml", "repos:\n  - just-a-string\n  - repo: meta\n")
        assert check_pins(tmp_path) == []
        write(tmp_path, ".pre-commit-config.yaml", "- not\n- a mapping\n")
        assert check_pins(tmp_path) == []
        write(tmp_path, ".pre-commit-config.yaml", "repos: [unbalanced\n")
        assert messages(check_pins(tmp_path)) == ["invalid YAML"]
