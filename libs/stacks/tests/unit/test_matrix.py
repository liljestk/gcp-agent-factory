from __future__ import annotations

from pathlib import Path

import pytest

from stacks.catalog import parse_catalog
from stacks.errors import StacksError
from stacks.matrix import compute
from stacks.modules import local_modules, module_sources

CATALOG = {
    "tiers": ["canary", "network"],
    "all-stacks-paths": ["mise.toml", ".github/workflows/"],
    "stacks": {
        "bootstrap": {"path": "stacks/bootstrap", "scope": "trust-root", "apply": "local"},
        "network": {
            "path": "stacks/network",
            "envs": ["dev", "prod"],
            "tier": "network",
            "inputs": ["config/network.yaml", "config/firewall/"],
        },
        "ci-canary": {"path": "stacks/ci-canary", "envs": ["dev"], "tier": "canary"},
    },
}


def write(root: Path, relative: str, text: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def module(source: str, name: str = "m") -> str:
    return f'module "{name}" {{\n  source = "{source}"\n}}\n'


def planned(root: Path, *changed: str) -> list[str]:
    return [instance.job_id for instance in compute(parse_catalog(CATALOG), root, changed).plan]


class TestCompute:
    def test_normalises_windows_and_dot_prefixed_paths_and_skips_blanks(
        self,
        tmp_path: Path,
    ) -> None:
        assert planned(tmp_path, "  .\\stacks\\network\\main.tf  ", "", "   ") == [
            "network/dev",
            "network/prod",
        ]

    def test_file_entries_match_exactly(self, tmp_path: Path) -> None:
        assert planned(tmp_path, "mise.toml.bak", "docs/mise.toml") == []

    def test_directory_entries_match_by_prefix_only(self, tmp_path: Path) -> None:
        assert planned(tmp_path, ".github/workflows-old/ci.yml") == []
        assert planned(tmp_path, ".github/workflows/ci.yml") == [
            "bootstrap/trust-root",
            "ci-canary/dev",
            "network/dev",
            "network/prod",
        ]

    def test_a_sibling_directory_with_a_shared_prefix_is_not_the_stack(
        self,
        tmp_path: Path,
    ) -> None:
        assert planned(tmp_path, "stacks/network-old/main.tf") == []

    @pytest.mark.parametrize("path", ["config/network.yaml", "config/firewall/rules.yaml"])
    def test_declared_inputs_affect_their_stack(self, tmp_path: Path, path: str) -> None:
        assert planned(tmp_path, path) == ["network/dev", "network/prod"]

    def test_undeclared_neighbours_of_inputs_do_not(self, tmp_path: Path) -> None:
        assert planned(tmp_path, "config/network.yaml.bak", "config/firewall-old/x") == []

    def test_every_stack_when_changed_is_none(self, tmp_path: Path) -> None:
        matrix = compute(parse_catalog(CATALOG), tmp_path, None)
        assert [i.job_id for i in matrix.plan] == [
            "bootstrap/trust-root",
            "ci-canary/dev",
            "network/dev",
            "network/prod",
        ]
        assert {group: len(jobs) for group, jobs in matrix.apply.items()} == {
            "canary/shared": 0,
            "canary/dev": 1,
            "canary/prod": 0,
            "network/shared": 0,
            "network/dev": 1,
            "network/prod": 1,
        }

    def test_json_document_lists_every_group(self, tmp_path: Path) -> None:
        document = compute(parse_catalog(CATALOG), tmp_path, ["stacks/ci-canary/main.tf"]).to_json()
        job = {
            "id": "ci-canary/dev",
            "stack": "ci-canary",
            "instance": "dev",
            "path": "stacks/ci-canary",
            "state_prefix": "dev/ci-canary/",
            "environment": "dev",
        }
        assert document == {
            "plan": [job],
            "apply": {
                "canary/shared": [],
                "canary/dev": [job],
                "canary/prod": [],
                "network/shared": [],
                "network/dev": [],
                "network/prod": [],
            },
        }

    def test_a_module_change_affects_the_stack(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/network/main.tf", module("../../modules/vpc"))
        write(tmp_path, "modules/vpc/main.tf")
        assert planned(tmp_path, "modules/vpc/variables.tf") == ["network/dev", "network/prod"]

    def test_using_another_stack_as_a_module_fails(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/network/main.tf", module("../bootstrap/sub"))
        with pytest.raises(StacksError, match="uses stacks/bootstrap/sub, which is inside stack"):
            planned(tmp_path, "docs/x.md")


class TestLocalModules:
    def test_follows_references_transitively(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/a/main.tf", module("../../modules/b"))
        write(tmp_path, "modules/b/main.tf", module("./c"))
        write(tmp_path, "modules/b/c/main.tf")
        assert local_modules(tmp_path, "stacks/a") == {"modules/b", "modules/b/c"}

    def test_reads_single_line_blocks_and_every_file_type(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/a/main.tf", 'module "x" { source = "../../modules/hcl" }\n')
        write(tmp_path, "stacks/a/dns.tofu", module("../../modules/tofu"))
        write(
            tmp_path,
            "stacks/a/extra.tf.json",
            '{"module": {"j": {"source": "../../modules/json"}}}',
        )
        write(
            tmp_path,
            "stacks/a/more.tofu.json",
            '{"module": [{"k": [{"source": "../../modules/list"}]}]}',
        )
        assert local_modules(tmp_path, "stacks/a") == {
            "modules/hcl",
            "modules/tofu",
            "modules/json",
            "modules/list",
        }

    def test_ignores_registry_and_provider_sources(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/a/main.tf",
            "terraform {\n  required_providers {\n    google = {\n"
            '      source = "hashicorp/google"\n    }\n  }\n}\n'
            + module("terraform-google-modules/network/google"),
        )
        write(tmp_path, "stacks/a/other.tf.json", '{"resource": {}}')
        assert local_modules(tmp_path, "stacks/a") == frozenset()

    def test_survives_cycles_and_self_references(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/a/main.tf", module("../../modules/b") + module("./", "self"))
        write(tmp_path, "modules/b/main.tf", module("../c"))
        write(tmp_path, "modules/c/main.tf", module("../b") + module("../../stacks/a", "back"))
        assert local_modules(tmp_path, "stacks/a") == {"modules/b", "modules/c"}

    def test_missing_directories_have_no_modules(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/a/main.tf", module("../../modules/gone"))
        assert local_modules(tmp_path, "stacks/a") == {"modules/gone"}
        assert local_modules(tmp_path, "stacks/missing") == frozenset()

    def test_skips_entries_that_are_not_files(self, tmp_path: Path) -> None:
        (tmp_path / "stacks" / "a" / "odd.tf").mkdir(parents=True)
        assert module_sources(tmp_path, "stacks/a") == []

    @pytest.mark.parametrize(
        ("file", "text", "message"),
        [
            ("main.tf", module("../../../outside"), "leaves the repository"),
            ("main.tf", 'module "v" {\n  source = "../${var.dir}"\n}\n', "must be a literal"),
            ("main.tf", 'module "l" {\n  source = local.dir\n}\n', "must be a literal string"),
            ("main.tf", 'module "n" {\n  version = "1"\n}\n', "must be a literal string"),
            ("main.tf", 'module "x" {\n', "isn't valid HCL"),
            ("a.tf.json", '{"module": {"j": {"source": "${var.x}"}}}', "must be a literal"),
            ("a.tf.json", '{"module": {"j": {"source": 5}}}', "must be a literal string"),
            ("a.tf.json", "{not json", "isn't a valid OpenTofu JSON configuration"),
            ("a.tf.json", '["not", "an", "object"]', "isn't a valid OpenTofu JSON"),
            ("a.tf.json", '{"module": {"j": "text"}}', "isn't a valid OpenTofu JSON"),
        ],
    )
    def test_fails_closed_on_what_it_cannot_follow(
        self,
        tmp_path: Path,
        file: str,
        text: str,
        message: str,
    ) -> None:
        write(tmp_path, f"stacks/a/{file}", text)
        with pytest.raises(StacksError, match=message):
            local_modules(tmp_path, "stacks/a")

    def test_fails_closed_on_undecodable_files(self, tmp_path: Path) -> None:
        path = tmp_path / "stacks" / "a" / "main.tf"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\xff\xfe\x00 not utf-8")
        with pytest.raises(StacksError, match="can't be read"):
            local_modules(tmp_path, "stacks/a")

    @pytest.mark.parametrize(
        ("link", "message"),
        [("stacks/a", "directories must not be symlinks"), ("stacks/a/main.tf", "files must")],
    )
    def test_rejects_symlinks(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        link: str,
        message: str,
    ) -> None:
        write(tmp_path, "stacks/a/main.tf")
        linked = tmp_path / link
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda self: self == linked or original(self))
        with pytest.raises(StacksError, match=message):
            local_modules(tmp_path, "stacks/a")
