"""Steps for the Claude Code hook features."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass

import pytest
from pytest_bdd import parsers, then, when

import guard_bash


@dataclass
class HookResult:
    """Exit code and stderr of one guard invocation."""

    exit_code: int = -1
    stderr: str = ""


@pytest.fixture
def hook_result() -> HookResult:
    return HookResult()


def _invoke(result: HookResult, raw: str) -> None:
    stderr = io.StringIO()
    result.exit_code = guard_bash.main(io.StringIO(raw), stderr)
    result.stderr = stderr.getvalue()


@when(parsers.parse('the agent runs "{command}" in the "{tool}" tool'))
def agent_runs(hook_result: HookResult, command: str, tool: str) -> None:
    _invoke(hook_result, json.dumps({"tool_name": tool, "tool_input": {"command": command}}))


@when(parsers.parse('the guard receives the raw input "{raw}"'))
def guard_receives(hook_result: HookResult, raw: str) -> None:
    _invoke(hook_result, raw)


@then(parsers.parse('the command is blocked because of "{reason}"'))
def command_blocked(hook_result: HookResult, reason: str) -> None:
    assert hook_result.exit_code == 2
    assert reason in hook_result.stderr


@then("the command is allowed")
def command_allowed(hook_result: HookResult) -> None:
    assert hook_result.exit_code == 0, hook_result.stderr
    assert hook_result.stderr == ""
