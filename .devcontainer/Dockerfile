# syntax=docker/dockerfile:1
# Canonical dev environment (ADR-0001). Images are pinned by digest; Renovate keeps them current.
FROM jdxcode/mise:2026.11.8@sha256:5c6e71a86c8c997c32d30a169b4269bec9d4681a804e29078bac8f44109f2edc AS mise

FROM mcr.microsoft.com/devcontainers/base:trixie@sha256:6ee2b4097c75d33e9a94d941577a3286e5d629434fba384688b06daeeaaeac99

# python3 runs the Claude Code hooks (stdlib only). Every other tool comes from mise.toml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise

USER vscode
ENV MISE_DATA_DIR=/home/vscode/.local/share/mise \
    MISE_TRUSTED_CONFIG_PATHS=/workspaces \
    UV_PROJECT_ENVIRONMENT=/home/vscode/.venv \
    UV_LINK_MODE=copy \
    PATH=/home/vscode/.local/share/mise/shims:/home/vscode/.local/bin:$PATH

RUN mise --version
