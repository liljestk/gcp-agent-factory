"""Repository-wide pytest configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def pytest_bdd_apply_tag(tag: str, function: Callable[..., object]) -> bool | None:  # noqa: ARG001
    """Treat ``@REQ-*`` Gherkin tags as traceability metadata, not pytest markers.

    Returning ``True`` tells pytest-bdd the tag is handled; ``None`` falls back to the
    default behaviour (the tag becomes a marker and must be registered).
    """
    if tag.startswith("REQ-"):
        return True
    return None
