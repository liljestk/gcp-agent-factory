from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from stacks.catalog import CATALOG_PATH, CatalogError, Instance, Mode, load_catalog, parse_catalog

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[4]

BASE: dict[str, Any] = {
    "tiers": ["canary", "foundation", "network"],
    "all-stacks-paths": ["mise.toml", ".github/workflows/"],
    "stacks": {
        "bootstrap": {"path": "infra/bootstrap", "scope": "trust-root", "apply": "local"},
        "github": {
            "path": "infra/github",
            "scope": "trust-root",
            "plan": "local",
            "apply": "local",
        },
        "foundation": {
            "path": "infra/foundation",
            "scope": "shared",
            "environment": "foundation",
            "tier": "foundation",
        },
        "network": {"path": "infra/network", "envs": ["dev", "prod"], "tier": "network"},
        "dns": {
            "path": "infra/dns",
            "scope": "shared",
            "environment": "foundation",
            "tier": "network",
            "inputs": ["config/dns.yaml", "config/zones/"],
        },
        "ci-canary": {"path": "infra/ci-canary", "envs": ["dev", "prod"], "tier": "canary"},
        "alpha": {"path": "infra/alpha", "envs": ["prod"], "tier": "canary"},
    },
}


def variant(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    data = copy.deepcopy(BASE)
    change(data)
    return data


def stack(name: str, **fields: object) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        entry = data["stacks"][name]
        for key, value in fields.items():
            if value is None:
                entry.pop(key, None)
            else:
                entry[key] = value

    return change


def top(key: str, value: object) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        if value is None:
            data.pop(key)
        else:
            data[key] = value

    return change


class TestParseCatalog:
    def test_builds_stacks_and_instances(self) -> None:
        catalog = parse_catalog(copy.deepcopy(BASE))
        by_name = {entry.name: entry for entry in catalog.stacks}
        assert catalog.tiers == ("canary", "foundation", "network")
        assert catalog.all_stacks_paths == ("mise.toml", ".github/workflows/")
        assert by_name["bootstrap"].plan is Mode.CI
        assert by_name["bootstrap"].apply is Mode.LOCAL
        assert by_name["bootstrap"].tier is None
        assert by_name["bootstrap"].instances == (
            Instance("bootstrap", "trust-root", "infra/bootstrap", None),
        )
        assert by_name["foundation"].instances == (
            Instance("foundation", "shared", "infra/foundation", "foundation"),
        )
        assert [i.environment for i in by_name["network"].instances] == ["dev", "prod"]
        assert by_name["dns"].inputs == ("config/dns.yaml", "config/zones/")
        assert by_name["network"].inputs == ()

    def test_orders_envs_and_strips_trailing_slash(self) -> None:
        data = variant(stack("network", envs=["prod", "dev"], path="infra/network/"))
        network = next(entry for entry in parse_catalog(data).stacks if entry.name == "network")
        assert network.path == "infra/network"
        assert [instance.key for instance in network.instances] == ["dev", "prod"]

    def test_all_stacks_paths_default_to_none(self) -> None:
        assert parse_catalog(variant(top("all-stacks-paths", None))).all_stacks_paths == ()

    def test_instance_identifiers(self) -> None:
        instance = Instance("network", "dev", "infra/network", "dev")
        assert instance.job_id == "network/dev"
        assert instance.state_prefix == "dev/network/"

    def test_apply_groups_cover_every_tier_and_key_in_order(self) -> None:
        groups = parse_catalog(copy.deepcopy(BASE)).apply_groups()
        assert list(groups) == [
            "canary/shared",
            "canary/dev",
            "canary/prod",
            "foundation/shared",
            "foundation/dev",
            "foundation/prod",
            "network/shared",
            "network/dev",
            "network/prod",
        ]
        assert [instance.stack for instance in groups["canary/prod"]] == ["alpha", "ci-canary"]
        assert [instance.stack for instance in groups["network/shared"]] == ["dns"]
        assert groups["foundation/dev"] == ()

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            ([], "catalog: must be a mapping with string keys"),
            ({1: "x"}, "catalog: must be a mapping with string keys"),
            (variant(top("extra", 1)), "catalog: has unknown keys: extra"),
            (variant(top("tiers", None)), "tiers: must be a list of strings"),
            (variant(top("tiers", "canary")), "tiers: must be a list of strings"),
            (variant(top("tiers", [1])), "tiers: must be a list of strings"),
            (variant(top("tiers", [])), "tiers: must be a non-empty list"),
            (variant(top("tiers", ["Canary"])), "tiers: must be a non-empty list"),
            (variant(top("tiers", ["a", "a"])), "tiers: must not repeat entries"),
            (variant(top("all-stacks-paths", ["../up"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["/abs"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["a\\b"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["./a"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["a//b"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["a b"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["$(id)"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", ["Docs/"])), "must be a lowercase repo-relative"),
            (variant(top("all-stacks-paths", [""])), "all-stacks-paths: must be a non-empty"),
            (variant(top("stacks", None)), "stacks: must be a mapping"),
            (variant(top("stacks", {"Bad": {}})), "stack 'Bad': name must be lowercase"),
            (variant(top("stacks", {"x": []})), "stack 'x': must be a mapping"),
            (variant(stack("network", extra=1)), "stack 'network': has unknown keys: extra"),
            (variant(stack("network", path=None)), "stack 'network' path: must be a non-empty"),
            (variant(stack("network", path=".")), "stack 'network' path: must be a lowercase"),
            (variant(stack("network", plan="maybe")), "stack 'network' plan: must be 'ci' or"),
            (variant(stack("network", plan="local")), "planned locally can't be applied by CI"),
            (variant(stack("network", scope="shared")), "set exactly one of 'envs' or 'scope'"),
            (variant(stack("network", envs=None)), "set exactly one of 'envs' or 'scope'"),
            (variant(stack("bootstrap", scope="dev")), "scope must be 'trust-root' or 'shared'"),
            (variant(stack("network", envs=[])), "envs must be a non-empty subset"),
            (variant(stack("network", envs=["qa"])), "envs must be a non-empty subset"),
            (variant(stack("bootstrap", apply="ci", tier="canary")), "only trust-root stacks"),
            (variant(stack("network", apply="local", plan="local")), "only trust-root stacks"),
            (variant(stack("bootstrap", tier="canary")), "a locally applied stack has no tier"),
            (variant(stack("network", tier=None)), "stack 'network' tier: must be a non-empty"),
            (variant(stack("network", tier="ops")), "tier 'ops' is not listed in 'tiers'"),
            (variant(stack("network", environment="dev")), "per-env stacks apply in the"),
            (variant(stack("bootstrap", environment="x")), "trust-root stacks have no GitHub"),
            (variant(stack("foundation", environment=None)), "environment: must be a non-empty"),
            (variant(stack("foundation", environment="dev")), "shared stacks apply in one of"),
            (variant(stack("dns", inputs="config")), "stack 'dns' inputs: must be a list"),
            (variant(stack("dns", inputs=["../x"])), "stack 'dns' inputs: must be a lowercase"),
            (variant(stack("alpha", path="infra/network")), "must not share or nest: alpha in"),
            (variant(stack("alpha", path="infra/network/sub")), "must not share or nest: alpha"),
        ],
    )
    def test_rejects_rule_violations(self, data: object, message: str) -> None:
        with pytest.raises(CatalogError) as caught:
            parse_catalog(data)
        assert message in str(caught.value)


class TestLoadCatalog:
    def test_reports_unreadable_file(self, tmp_path: Path) -> None:
        with pytest.raises(CatalogError, match="can't be read"):
            load_catalog(tmp_path / "missing.yaml")

    def test_reports_invalid_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "stacks.yaml"
        path.write_text("tiers: [unclosed\n", encoding="utf-8")
        with pytest.raises(CatalogError, match="isn't valid YAML"):
            load_catalog(path)

    def test_rejects_repeated_keys_at_any_depth(self, tmp_path: Path) -> None:
        path = tmp_path / "stacks.yaml"
        path.write_text(
            "tiers: [canary]\nstacks:\n  a:\n    path: x\n  b: [{k: 1}]\n  a:\n    path: y\n",
            encoding="utf-8",
        )
        with pytest.raises(CatalogError, match="repeats keys: a"):
            load_catalog(path)
        path.write_text("tiers: [canary]\nlist:\n  - {k: 1, k: 2}\n", encoding="utf-8")
        with pytest.raises(CatalogError, match="repeats keys: k"):
            load_catalog(path)

    def test_an_empty_file_is_not_a_catalog(self, tmp_path: Path) -> None:
        path = tmp_path / "stacks.yaml"
        path.write_text("", encoding="utf-8")
        with pytest.raises(CatalogError, match="catalog: must be a mapping"):
            load_catalog(path)

    def test_the_repository_catalog_keeps_its_guarantees(self) -> None:
        catalog = load_catalog(REPO_ROOT / CATALOG_PATH)
        stacks = {entry.name: entry for entry in catalog.stacks}
        assert (stacks["bootstrap"].plan, stacks["bootstrap"].apply) == (Mode.CI, Mode.LOCAL)
        assert (stacks["github"].plan, stacks["github"].apply) == (Mode.LOCAL, Mode.LOCAL)
        assert stacks["bootstrap"].path == "platforms/landing-zone/infra/bootstrap"
        assert stacks["github"].path == "platforms/landing-zone/infra/github"
        assert catalog.all_stacks_paths == (
            "mise.toml",
            "platforms/stacks.yaml",
            ".github/workflows/",
            ".github/actions/",
            "libs/stacks/",
            "pyproject.toml",
            "uv.lock",
            "justfile",
        )
