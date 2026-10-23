from __future__ import annotations

import io
import json
import runpy
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import format_on_edit
import guard_bash

if TYPE_CHECKING:
    from pathlib import Path


def payload(**tool_input: object) -> str:
    return json.dumps({"tool_name": "Edit", "tool_input": tool_input})


class TestGuardBash:
    @pytest.mark.parametrize(
        "data",
        [
            ["not", "a", "mapping"],
            {"tool_name": "Bash", "tool_input": "not a mapping"},
            {"tool_name": "Bash", "tool_input": {"command": 42}},
        ],
        ids=["list", "tool-input-string", "command-not-string"],
    )
    def test_unexpected_payload_shapes_are_allowed(self, data: object) -> None:
        assert guard_bash.evaluate(data) is None

    def test_runs_as_a_script(self, monkeypatch: pytest.MonkeyPatch) -> None:
        raw = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path(guard_bash.__file__, run_name="__main__")
        assert excinfo.value.code == 0


class TestFormatOnEdit:
    @pytest.mark.parametrize(
        ("path", "installed", "expected"),
        [
            ("a.py", {"uv"}, ["/bin/uv", "run", "--frozen", "--quiet", "ruff", "format", "a.py"]),
            ("a.py", set(), None),
            ("main.tf", {"tofu"}, ["/bin/tofu", "fmt", "main.tf"]),
            ("x.tftest.hcl", {"tofu"}, ["/bin/tofu", "fmt", "x.tftest.hcl"]),
            ("main.tf", set(), None),
            ("README.md", {"uv", "tofu"}, None),
        ],
    )
    def test_formatter_for(
        self,
        monkeypatch: pytest.MonkeyPatch,
        path: str,
        installed: set[str],
        expected: list[str] | None,
    ) -> None:
        monkeypatch.setattr(
            "shutil.which",
            lambda name: f"/bin/{name}" if name in installed else None,
        )
        assert format_on_edit.formatter_for(path) == expected

    @pytest.mark.parametrize(
        "data",
        [[], {"tool_input": "x"}, {"tool_input": {}}, {"tool_input": {"file_path": ""}}],
        ids=["list", "tool-input-string", "no-path", "empty-path"],
    )
    def test_edited_path_rejects_unusable_payloads(self, data: object) -> None:
        assert format_on_edit.edited_path(data) is None

    def test_main_skips_invalid_json_missing_files_and_unknown_types(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.write_text("x", encoding="utf-8")
        assert format_on_edit.main(io.StringIO("not json")) == 0
        assert format_on_edit.main(io.StringIO(payload(file_path=str(tmp_path / "gone.py")))) == 0
        assert format_on_edit.main(io.StringIO(payload(file_path=str(notes)))) == 0

    def test_main_runs_the_formatter(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "main.tf"
        source.write_text("x", encoding="utf-8")
        calls: list[list[str]] = []
        monkeypatch.setattr("shutil.which", lambda name: f"/bin/{name}")
        monkeypatch.setattr(
            "subprocess.run",
            lambda command, **_: calls.append(command),
        )
        assert format_on_edit.main(io.StringIO(payload(file_path=str(source)))) == 0
        assert calls == [["/bin/tofu", "fmt", str(source)]]

    @pytest.mark.parametrize(
        "error",
        [subprocess.TimeoutExpired(cmd="tofu", timeout=30), OSError("missing")],
        ids=["timeout", "os-error"],
    )
    def test_main_never_fails_on_formatter_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        error: Exception,
    ) -> None:
        source = tmp_path / "main.tf"
        source.write_text("x", encoding="utf-8")

        def explode(*_: object, **__: object) -> None:
            raise error

        monkeypatch.setattr("shutil.which", lambda name: f"/bin/{name}")
        monkeypatch.setattr("subprocess.run", explode)
        assert format_on_edit.main(io.StringIO(payload(file_path=str(source)))) == 0

    def test_runs_as_a_script(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path(format_on_edit.__file__, run_name="__main__")
        assert excinfo.value.code == 0
