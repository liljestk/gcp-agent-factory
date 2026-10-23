---
status: accepted
date: 2026-10-23
decision-makers: liljestk
---

# ADR-0002: Python and Google ADK 2.x for agents

## Context and problem statement

We need a multi-agent framework that runs well on GCP, supports deterministic orchestration and human-in-the-loop, emits OpenTelemetry, and can talk agent-to-agent.

## Decision

Build agents in **Python 3.13 with Google ADK 2.x**:

- ADK 2 **graph workflows** for deterministic orchestration, plus resumability for pause/resume.
- ADK **plugins** as the single hook point for cross-cutting guards (kill switch, budget, telemetry, tool policy), shipped in `libs/agent-core`.
- **A2A** for synchronous agent-to-agent calls.
- Pin the exact ADK version in `uv.lock`; check API details against the docs when Phase 3 starts.

## Consequences

- Good: first-party Vertex AI integration, OpenTelemetry built in, and deploy paths to Cloud Run and Agent Engine.
- Good: an official Temporal plugin exists, which keeps ADR-0004's escape hatch real.
- Bad: ADK 2.x moves fast; the API needs pinning and a Renovate cadence with eval gates.

## Alternatives considered

- **LangGraph / CrewAI**: capable, but less GCP-native and further from the demo's "Google ADK" goal.
- **ADK TypeScript/Go/Java**: the Python ADK is the most mature and has the richest examples.

## Enforcement

The agent scaffold (`agent-new` skill, Phase 3) generates ADK-based packages wired to `agent-core`; agent evals gate ADK upgrades.
