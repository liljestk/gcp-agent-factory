"""Evaluate the WIF trust condition and gates (REQ-LZ-001, REQ-LZ-002) against token claims.

The CEL comes from modules/wif-github/gates.json.tftpl, the same template the module renders,
so these cases test what gets deployed. As in Google's token exchange, the attribute mapping is
evaluated first and the trust condition can then use the mapped attributes. The live provider's
expressions are checked against the same cases by the deployed identity scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path
from string import Template

import celpy
import pytest
from celpy.adapter import json_to_cel

TEMPLATE = Path(__file__).resolve().parents[2] / "modules" / "wif-github" / "gates.json.tftpl"
REPOSITORY = "liljestk/gcp-agent-factory"
OWNER = "4373495"
BOT = "29139614"
TOFU = f"{REPOSITORY}/.github/workflows/tofu.yml@refs/heads/main"
OTHER = f"{REPOSITORY}/.github/workflows/drift.yml@refs/heads/main"

BASE = {
    "repository": REPOSITORY,
    "repository_id": "1431415117",
    "repository_owner_id": OWNER,
    "actor_id": OWNER,
    "event_name": "push",
    "ref": "refs/heads/main",
    "workflow_ref": TOFU,
    "job_workflow_ref": TOFU,
    "runner_environment": "github-hosted",
    "sub": f"repo:{REPOSITORY}:ref:refs/heads/main",
}


def gates() -> dict[str, str]:
    rendered = Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        repository=REPOSITORY,
        repository_id="1431415117",
        repository_owner_id=OWNER,
        owner_actor_id=OWNER,
        apply_workflow=".github/workflows/tofu.yml",
    )
    document = json.loads(rendered)
    assert set(document) == {"condition", "plan", "deploy"}
    return {name: str(expression) for name, expression in document.items()}


def run(expression: str, activation: dict[str, dict[str, str]]) -> str:
    environment = celpy.Environment()
    program = environment.program(environment.compile(expression))
    return str(program.evaluate({name: json_to_cel(value) for name, value in activation.items()}))


def exchange(**claims: str | None) -> dict[str, str]:
    """Map the claims like Google's STS: plan and deploy first, then the trust condition."""
    assertion = {key: value for key, value in {**BASE, **claims}.items() if value is not None}
    expressions = gates()
    attribute = {
        gate: run(expressions[gate], {"assertion": assertion}) for gate in ("plan", "deploy")
    }
    accepted = run(expressions["condition"], {"assertion": assertion, "attribute": attribute})
    return {**attribute, "accepted": accepted}


@pytest.mark.parametrize(
    ("claims", "accepted"),
    [
        ({}, "True"),
        ({"repository_id": "999", "repository_owner_id": "555"}, "False"),
        ({"repository_id": "999"}, "False"),
        ({"repository_owner_id": "555"}, "False"),
        ({"event_name": "pull_request", "ref": "refs/pull/7/merge", "actor_id": BOT}, "False"),
        ({"event_name": "push", "ref": "refs/heads/feature"}, "False"),
    ],
    ids=[
        "this-repository",
        "a-fork",
        "same-name-new-repository",
        "another-owner",
        "a-bot-pull-request-gets-no-token",
        "a-branch-push-gets-no-token",
    ],
)
def test_only_gated_tokens_from_this_repository_are_exchanged(
    claims: dict[str, str],
    accepted: str,
) -> None:
    assert exchange(**claims)["accepted"] == accepted


@pytest.mark.parametrize(
    ("claims", "gate"),
    [
        ({"event_name": "pull_request", "ref": "refs/pull/7/merge"}, "allowed"),
        ({"event_name": "pull_request", "ref": "refs/pull/7/merge", "actor_id": BOT}, "denied"),
        ({"event_name": "workflow_dispatch", "ref": "refs/heads/renovate/x"}, "allowed"),
        ({"event_name": "workflow_dispatch", "ref": "refs/heads/x", "actor_id": BOT}, "denied"),
        ({"event_name": "push", "ref": "refs/heads/feature"}, "denied"),
        ({"event_name": "push"}, "allowed"),
        ({"event_name": "schedule", "actor_id": BOT}, "allowed"),
        ({"event_name": "pull_request_target", "ref": "refs/heads/main"}, "denied"),
        ({"event_name": "workflow_run", "ref": "refs/heads/main"}, "denied"),
        ({"event_name": "issue_comment", "ref": "refs/heads/main"}, "denied"),
        ({"event_name": "merge_group", "ref": "refs/heads/gh-readonly-queue/main/x"}, "denied"),
        ({"event_name": "push", "ref": "refs/tags/main"}, "denied"),
    ],
    ids=[
        "owner-pull-request",
        "bot-pull-request",
        "owner-dispatch-on-a-branch",
        "bot-dispatch",
        "push-to-a-branch",
        "push-to-main",
        "nightly-schedule",
        "pull-request-target",
        "workflow-run",
        "issue-comment",
        "merge-group",
        "tag-named-main",
    ],
)
def test_plan_gate(claims: dict[str, str], gate: str) -> None:
    assert exchange(**claims)["plan"] == gate


@pytest.mark.parametrize(
    ("claims", "environment"),
    [
        ({"environment": "prod"}, "prod"),
        ({"environment": "foundation"}, "foundation"),
        ({"environment": "prod", "ref": "refs/heads/feature"}, "none"),
        ({"environment": "prod", "workflow_ref": OTHER, "job_workflow_ref": OTHER}, "none"),
        ({"environment": "prod", "workflow_ref": OTHER}, "none"),
        ({"environment": "prod", "runner_environment": "self-hosted"}, "none"),
        ({"environment": None}, "none"),
        ({"environment": "dev", "event_name": "workflow_dispatch"}, "none"),
        ({"environment": "dev", "event_name": "schedule"}, "none"),
        ({"environment": "dev", "event_name": "pull_request_target"}, "none"),
        ({"environment": "dev", "event_name": "issue_comment"}, "none"),
        ({"environment": "dev", "event_name": "workflow_run"}, "none"),
        ({"environment": "dev", "event_name": "repository_dispatch"}, "none"),
    ],
    ids=[
        "push-of-tofu-on-main-in-prod",
        "push-of-tofu-on-main-in-foundation",
        "tofu-on-a-branch",
        "another-workflow",
        "tofu-called-by-another-workflow",
        "self-hosted-runner",
        "no-environment",
        "manual-dispatch",
        "schedule",
        "pull-request-target",
        "issue-comment",
        "workflow-run",
        "repository-dispatch",
    ],
)
def test_deploy_gate(claims: dict[str, str | None], environment: str) -> None:
    assert exchange(**claims)["deploy"] == environment
