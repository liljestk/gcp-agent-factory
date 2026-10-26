"""Turn a set of changed files into the CI plan and apply jobs (REQ-LZ-005, REQ-LZ-006)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from stacks.catalog import Mode
from stacks.errors import StacksError
from stacks.modules import local_modules

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from stacks.catalog import Catalog, Instance


@dataclass(frozen=True, slots=True)
class Matrix:
    """The jobs a change needs.

    Attributes:
        plan: Instances CI plans, sorted by job ID.
        apply: Every apply group, in apply order, mapped to the affected instances in it.
            Unaffected groups map to an empty tuple, so workflows can reference fixed keys.
    """

    plan: tuple[Instance, ...]
    apply: dict[str, tuple[Instance, ...]]

    def to_json(self) -> dict[str, object]:
        """Return the JSON document the workflows read."""
        return {
            "plan": [_entry(instance) for instance in self.plan],
            "apply": {
                group: [_entry(instance) for instance in instances]
                for group, instances in self.apply.items()
            },
        }


def compute(catalog: Catalog, root: Path, changed: Iterable[str] | None) -> Matrix:
    """Return the jobs for ``changed`` repo-relative paths, or for every stack if ``None``.

    Raises:
        StacksError: The module graph can't be built, or a stack uses a module that lies inside
            another stack.
    """
    modules = {stack.name: local_modules(root, stack.path) for stack in catalog.stacks}
    problems = boundary_problems(catalog, modules)
    if problems:
        raise StacksError("; ".join(problems))
    names = (
        {stack.name for stack in catalog.stacks}
        if changed is None
        else affected_stacks(catalog, modules, changed)
    )
    plan = sorted(
        (
            instance
            for stack in catalog.stacks
            if stack.name in names and stack.plan is Mode.CI
            for instance in stack.instances
        ),
        key=lambda instance: instance.job_id,
    )
    apply = {
        group: tuple(instance for instance in instances if instance.stack in names)
        for group, instances in catalog.apply_groups().items()
    }
    return Matrix(plan=tuple(plan), apply=apply)


def affected_stacks(
    catalog: Catalog,
    modules: Mapping[str, frozenset[str]],
    changed: Iterable[str],
) -> set[str]:
    """Return the names of the stacks that ``changed`` paths affect.

    A path affects a stack when it lies in the stack's directory, in a module the stack uses
    (``modules``, by stack name) or matches one of its ``inputs``. A path matching any
    ``all-stacks-paths`` entry affects every stack.
    """
    paths = [path for path in (_normalise(entry) for entry in changed) if path]
    if any(_matches(path, entry) for path in paths for entry in catalog.all_stacks_paths):
        return {stack.name for stack in catalog.stacks}
    return {
        stack.name
        for stack in catalog.stacks
        if any(
            _matches(path, entry)
            for path in paths
            for entry in (f"{stack.path}/", *sorted(modules[stack.name]), *stack.inputs)
        )
    }


def boundary_problems(catalog: Catalog, modules: Mapping[str, frozenset[str]]) -> list[str]:
    """Report stacks that use a module inside another stack's directory.

    Such a module would let one stack's change reach another stack's apply, including
    trust-root code reaching a CI apply (ADR-0018).
    """
    return [
        f"stack {stack.name!r} uses {module}, which is inside stack {other.name!r}"
        for stack in catalog.stacks
        for module in sorted(modules[stack.name])
        for other in catalog.stacks
        if other is not stack and f"{module}/".startswith(f"{other.path}/")
    ]


def _normalise(path: str) -> str:
    return path.strip().replace("\\", "/").removeprefix("./")


def _matches(path: str, entry: str) -> bool:
    """A trailing ``/`` makes ``entry`` a directory prefix; module directories never have one."""
    if entry.endswith("/"):
        return path.startswith(entry)
    return path == entry or path.startswith(f"{entry}/")


def _entry(instance: Instance) -> dict[str, str | None]:
    return {
        "id": instance.job_id,
        "stack": instance.stack,
        "instance": instance.key,
        "path": instance.path,
        "state_prefix": instance.state_prefix,
        "environment": instance.environment,
    }
