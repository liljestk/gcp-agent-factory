# Task runner. CI jobs call these same recipes, so a green `just check` locally means a green CI.
# On Windows, run inside the devcontainer (see AGENTS.md).

set shell := ["bash", "-euo", "pipefail", "-c"]

py_packages := `find libs -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tr '\n' ' '`
tofu_modules := `find modules -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tr '\n' ' '`

# List recipes
default:
    @just --list

# Install pinned tools, Python deps and git hooks
setup:
    mise install
    uv sync --all-packages --frozen
    uv run pre-commit install --install-hooks

# Auto-fix formatting and safe lint fixes
fmt:
    uv run ruff check --fix .
    uv run ruff format .
    tofu fmt -recursive modules

# Every gate CI runs
check: lint test test-iac repo-checks secrets

# All linters
lint: lint-python lint-iac lint-repo

# ruff + mypy (strict)
lint-python:
    uv run ruff check .
    uv run ruff format --check .
    for pkg in {{ py_packages }}; do uv run mypy "$pkg"; done
    uv run mypy .claude/hooks conftest.py
    uv run mypy tests

# tofu fmt + tflint
lint-iac:
    tofu fmt -check -recursive modules
    tflint --init --config "$PWD/.tflint.hcl"
    tflint --recursive --config "$PWD/.tflint.hcl"

# GitHub Actions, workflow security and markdown
lint-repo:
    actionlint
    zizmor .github
    markdownlint-cli2

# Unit + BDD tests with the 100% coverage gate
test *args:
    uv run pytest {{ args }}

# `tofu test` for every reusable module (offline, no credentials)
test-iac:
    for m in {{ tofu_modules }}; do (cd "$m" && tofu init -backend=false -input=false >/dev/null && tofu test); done

# Repo conventions: skills, ADRs, traceability, coverage pragmas, pinned dependencies
repo-checks:
    uv run repo-checks all

# Secret scan of the working tree
secrets:
    gitleaks dir . --redact --no-banner --config .gitleaks.toml
