from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stacks.errors import StacksError
from stacks.hcl import ConfigFile, config_paths, contains_key, is_override, load_config

if TYPE_CHECKING:
    from pathlib import Path


class TestConfigPaths:
    def test_tofu_files_shadow_their_tf_twins(self, tmp_path: Path) -> None:
        for name in ("a.tf", "a.tofu", "b.tf.json", "b.tofu.json", "c.tf", "d.tofu.json", "e.txt"):
            (tmp_path / name).write_text("", encoding="utf-8")
        (tmp_path / "dir.tf").mkdir()
        assert [path.name for path in config_paths(tmp_path)] == [
            "a.tofu",
            "b.tofu.json",
            "c.tf",
            "d.tofu.json",
        ]

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("override.tf", True),
            ("backend_override.tofu", True),
            ("x_override.tf.json", True),
            ("overrides.tf", False),
            ("main.tf", False),
            ("override.txt", False),
        ],
    )
    def test_override_files(self, name: str, *, expected: bool) -> None:
        assert is_override(name) is expected

    def test_contains_key_searches_nested_structures(self) -> None:
        assert contains_key({"a": [{"b": {"provisioner": []}}]}, "provisioner")
        assert not contains_key({"a": [1, "provisioner"]}, "provisioner")


def config(document: dict[str, object], *, json_syntax: bool = False) -> ConfigFile:
    return ConfigFile(where="x.tf", text="", document=document, json_syntax=json_syntax)


def load(tmp_path: Path, name: str, text: str) -> ConfigFile:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return load_config(path, name)


class TestBlocks:
    def test_hcl_blocks_with_labels_and_nested_blocks(self, tmp_path: Path) -> None:
        parsed = load(
            tmp_path,
            "main.tf",
            'resource "terraform_data" "y" {\n'
            '  provisioner "local-exec" {\n    command = "id"\n  }\n}\n'
            "terraform {\n  encryption {\n    state {\n      enforced = true\n    }\n  }\n}\n",
        )
        ((labels, body),) = parsed.blocks("resource", 2)
        assert labels == ("terraform_data", "y")
        assert [label for label, _ in parsed.blocks_in(body, "provisioner", 1)] == [("local-exec",)]
        ((_, terraform),) = parsed.blocks("terraform", 0)
        ((_, encryption),) = parsed.blocks_in(terraform, "encryption", 0)
        ((_, state),) = parsed.blocks_in(encryption, "state", 0)
        assert state == {"enforced": True}

    def test_json_blocks_accept_objects_and_lists(self, tmp_path: Path) -> None:
        parsed = load(
            tmp_path,
            "main.tf.json",
            '{"resource": {"a_b": {"one": {}, "two": [{"x": 1}]}}, "terraform": [{}]}',
        )
        assert [labels for labels, _ in parsed.blocks("resource", 2)] == [
            ("a_b", "one"),
            ("a_b", "two"),
        ]
        assert parsed.blocks("terraform", 0) == [((), {})]

    def test_absent_blocks_are_empty(self) -> None:
        assert config({}).blocks("module", 1) == []

    @pytest.mark.parametrize(
        ("document", "json_syntax"),
        [
            ({"module": {"x": {}}}, False),
            ({"module": ["not a block"]}, False),
            ({"module": {"x": "not a block"}}, True),
        ],
        ids=["hcl-section-not-a-list", "hcl-item-not-a-block", "json-body-not-an-object"],
    )
    def test_unexpected_shapes_fail(
        self, document: dict[str, object], *, json_syntax: bool
    ) -> None:
        with pytest.raises(StacksError, match="module blocks have an unexpected shape"):
            config(document, json_syntax=json_syntax).blocks("module", 1)


class TestLiteral:
    @pytest.mark.parametrize(
        ("value", "json_syntax", "expected"),
        [
            ('"../x"', False, "../x"),
            ("${local.x}", False, None),
            ('"${var.x}/y"', False, None),
            ("bare", False, None),
            ('"', False, None),
            (5, False, None),
            ("../x", True, "../x"),
            ("${var.x}", True, None),
            (None, True, None),
        ],
    )
    def test_only_string_literals_have_a_value(
        self,
        value: object,
        *,
        json_syntax: bool,
        expected: str | None,
    ) -> None:
        assert config({}, json_syntax=json_syntax).literal(value) == expected


class TestLineOf:
    def test_finds_the_first_matching_line(self) -> None:
        parsed = ConfigFile(where="x", text="a\nb = 1\nb = 2\n", document={}, json_syntax=False)
        assert parsed.line_of(r"b =") == 2
        assert parsed.line_of(r"missing") is None


class TestLoadConfig:
    def test_reports_unreadable_files(self, tmp_path: Path) -> None:
        with pytest.raises(StacksError, match="can't be read"):
            load_config(tmp_path / "missing.tf", "missing.tf")

    @pytest.mark.parametrize(
        ("name", "text", "message"),
        [
            ("a.tf", "module {\n", "isn't valid HCL"),
            ("a.tf.json", "{nope", "isn't a valid OpenTofu JSON configuration"),
            ("a.tf.json", "[1, 2]", "isn't a valid OpenTofu JSON configuration"),
        ],
    )
    def test_reports_invalid_syntax(
        self, tmp_path: Path, name: str, text: str, message: str
    ) -> None:
        with pytest.raises(StacksError, match=message):
            load(tmp_path, name, text)
