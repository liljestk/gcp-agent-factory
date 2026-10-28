"""The stack catalog: every OpenTofu root module, its instances and who may run it.

The catalog lives in ``platforms/stacks.yaml`` (spec 002). A stack has either ``envs`` (one
instance per environment, applied in the GitHub environment of the same name) or a ``scope``:
``shared`` (one instance, applied in ``environment``) or ``trust-root`` (one instance, applied
only by the owner, ADR-0018). ``plan`` and ``apply`` default to ``ci``; ``inputs`` lists files
outside the stack's directory that it reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import yaml

from stacks.errors import StacksError

CATALOG_PATH: Final = Path("platforms") / "stacks.yaml"
TRUST_ROOT: Final = "trust-root"
SHARED: Final = "shared"
ENVS: Final = ("dev", "prod")
APPLY_KEYS: Final = (SHARED, *ENVS)
# Shared state is written by ci-foundation, which only the foundation environment can reach.
SHARED_ENVIRONMENTS: Final = ("foundation",)
NAME_PATTERN: Final = re.compile(r"^[a-z][a-z0-9-]*$")
# Lowercase segments, optionally dot-prefixed; no ".", "..", spaces, shell characters or "\".
_SEGMENT: Final = r"\.?[a-z0-9_][a-z0-9._-]*"
PATH_PATTERN: Final = re.compile(rf"^{_SEGMENT}(?:/{_SEGMENT})*/?$")
CATALOG_KEYS: Final = frozenset({"tiers", "all-stacks-paths", "stacks"})
STACK_KEYS: Final = frozenset(
    {"path", "plan", "apply", "tier", "envs", "scope", "environment", "inputs"},
)


class CatalogError(StacksError):
    """The catalog is missing, malformed or breaks a rule."""


class Mode(StrEnum):
    """Who runs a stack's plan or apply."""

    CI = "ci"
    LOCAL = "local"


@dataclass(frozen=True, slots=True)
class Instance:
    """One state of a stack: the stack in one environment or scope.

    Attributes:
        stack: Name of the stack.
        key: Environment or scope (``trust-root``, ``shared``, ``dev`` or ``prod``).
        path: Repo-relative directory of the root module.
        environment: GitHub environment that applies it, or ``None`` for trust-root stacks.
    """

    stack: str
    key: str
    path: str
    environment: str | None

    @property
    def job_id(self) -> str:
        """Identifier used in job names: ``<stack>/<key>``."""
        return f"{self.stack}/{self.key}"

    @property
    def state_prefix(self) -> str:
        """Prefix of the instance's state in the state bucket: ``<key>/<stack>/``."""
        return f"{self.key}/{self.stack}/"


@dataclass(frozen=True, slots=True)
class Stack:
    """A root module and how CI may run it.

    Attributes:
        name: Kebab-case stack name.
        path: Repo-relative directory of the root module.
        plan: Whether CI or only the owner plans it.
        apply: Whether CI or only the owner applies it.
        tier: Apply tier for CI-applied stacks, ``None`` for locally applied ones.
        instances: One instance per environment or scope.
        inputs: Paths outside the stack and its modules that it reads; a trailing ``/`` marks a
            directory.
    """

    name: str
    path: str
    plan: Mode
    apply: Mode
    tier: str | None
    instances: tuple[Instance, ...]
    inputs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Catalog:
    """All stacks, the apply order and the paths that affect every stack."""

    tiers: tuple[str, ...]
    all_stacks_paths: tuple[str, ...]
    stacks: tuple[Stack, ...]

    def apply_groups(self) -> dict[str, tuple[Instance, ...]]:
        """Map every apply group ``<tier>/<key>`` to its instances, in apply order.

        Every tier gets a ``shared``, ``dev`` and ``prod`` group, in that order, so workflows can
        rely on fixed keys. Instances in a group are sorted by stack name.
        """
        return {
            f"{tier}/{key}": tuple(
                instance
                for stack in sorted(self.stacks, key=lambda entry: entry.name)
                if stack.tier == tier
                for instance in stack.instances
                if instance.key == key
            )
            for tier in self.tiers
            for key in APPLY_KEYS
        }


def load_catalog(path: Path) -> Catalog:
    """Read and validate the catalog at ``path``.

    Raises:
        CatalogError: The file can't be read, isn't YAML, repeats a key, or breaks a rule.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise _invalid(str(path), f"can't be read ({error.strerror})") from error
    try:
        _reject_duplicate_keys(yaml.compose(text, Loader=yaml.SafeLoader))
        data: object = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise _invalid(str(path), f"isn't valid YAML ({error})") from error
    return parse_catalog(data)


def parse_catalog(data: object) -> Catalog:
    """Validate parsed YAML and build the catalog.

    Raises:
        CatalogError: A rule is broken; the message names the stack and the rule.
    """
    top = _mapping(data, "catalog")
    _check_keys(top, CATALOG_KEYS, "catalog")
    tiers = _names(top.get("tiers"), "tiers")
    all_stacks_paths = _paths(top.get("all-stacks-paths", []), "all-stacks-paths")
    where = "stacks"
    stacks = tuple(
        _parse_stack(name, raw, tiers) for name, raw in _mapping(top.get(where), where).items()
    )
    nested = sorted(
        f"{inner.name} in {outer.name}"
        for outer in stacks
        for inner in stacks
        if inner is not outer and f"{inner.path}/".startswith(f"{outer.path}/")
    )
    if nested:
        raise _invalid(where, f"paths must not share or nest: {', '.join(nested)}")
    return Catalog(tiers=tiers, all_stacks_paths=all_stacks_paths, stacks=stacks)


def _parse_stack(name: str, raw: object, tiers: tuple[str, ...]) -> Stack:
    where = f"stack {name!r}"
    if not NAME_PATTERN.match(name):
        raise _invalid(where, "name must be lowercase kebab-case")
    data = _mapping(raw, where)
    _check_keys(data, STACK_KEYS, where)
    path = _path(data.get("path"), f"{where} path").removesuffix("/")
    plan = _mode(data.get("plan", Mode.CI.value), f"{where} plan")
    apply = _mode(data.get("apply", Mode.CI.value), f"{where} apply")
    if plan is Mode.LOCAL and apply is Mode.CI:
        raise _invalid(where, "a stack planned locally can't be applied by CI")
    keys = _instance_keys(data, where)
    if (keys == (TRUST_ROOT,)) != (apply is Mode.LOCAL):
        raise _invalid(where, "only trust-root stacks are applied locally, and always (ADR-0018)")
    tier = _tier(data, apply, tiers, where)
    environments = _environments(data, keys, where)
    return Stack(
        name=name,
        path=path,
        plan=plan,
        apply=apply,
        tier=tier,
        instances=tuple(Instance(name, key, path, environments[key]) for key in keys),
        inputs=_paths(data.get("inputs", []), f"{where} inputs"),
    )


def _instance_keys(data: dict[str, object], where: str) -> tuple[str, ...]:
    if ("envs" in data) == ("scope" in data):
        raise _invalid(where, "set exactly one of 'envs' or 'scope'")
    if "scope" in data:
        scope = _string(data["scope"], f"{where} scope")
        if scope not in (TRUST_ROOT, SHARED):
            raise _invalid(where, f"scope must be {TRUST_ROOT!r} or {SHARED!r}")
        return (scope,)
    envs = _strings(data["envs"], f"{where} envs")
    if not envs or not set(envs) <= set(ENVS):
        raise _invalid(where, f"envs must be a non-empty subset of {', '.join(ENVS)}")
    return tuple(env for env in ENVS if env in envs)


def _tier(data: dict[str, object], apply: Mode, tiers: tuple[str, ...], where: str) -> str | None:
    if apply is Mode.LOCAL:
        if "tier" in data:
            raise _invalid(where, "a locally applied stack has no tier")
        return None
    tier = _string(data.get("tier"), f"{where} tier")
    if tier not in tiers:
        raise _invalid(where, f"tier {tier!r} is not listed in 'tiers'")
    return tier


def _environments(
    data: dict[str, object],
    keys: tuple[str, ...],
    where: str,
) -> dict[str, str | None]:
    if keys[0] in ENVS:
        if "environment" in data:
            raise _invalid(where, "per-env stacks apply in the environment of the same name")
        return {key: key for key in keys}
    if keys[0] == TRUST_ROOT:
        if "environment" in data:
            raise _invalid(where, "trust-root stacks have no GitHub environment")
        return {TRUST_ROOT: None}
    environment = _string(data.get("environment"), f"{where} environment")
    if environment not in SHARED_ENVIRONMENTS:
        allowed = ", ".join(SHARED_ENVIRONMENTS)
        raise _invalid(where, f"shared stacks apply in one of: {allowed}")
    return {SHARED: environment}


def _mode(value: object, where: str) -> Mode:
    text = _string(value, where)
    try:
        return Mode(text)
    except ValueError as error:
        raise _invalid(where, f"must be 'ci' or 'local', not {text!r}") from error


def _paths(value: object, where: str) -> tuple[str, ...]:
    return tuple(_path(entry, where) for entry in _strings(value, where))


def _path(value: object, where: str) -> str:
    text = _string(value, where)
    if not PATH_PATTERN.match(text):
        raise _invalid(where, f"must be a lowercase repo-relative path, not {text!r}")
    return text


def _names(value: object, where: str) -> tuple[str, ...]:
    names = _strings(value, where)
    if not names or not all(NAME_PATTERN.match(name) for name in names):
        raise _invalid(where, "must be a non-empty list of lowercase kebab-case names")
    return names


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _invalid(where, "must be a list of strings")
    items = tuple(str(item) for item in value)
    if len(set(items)) != len(items):
        raise _invalid(where, "must not repeat entries")
    return items


def _string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid(where, "must be a non-empty string")
    return value


def _mapping(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _invalid(where, "must be a mapping with string keys")
    return {str(key): item for key, item in value.items()}


def _check_keys(data: dict[str, object], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise _invalid(where, f"has unknown keys: {', '.join(unknown)}")


def _reject_duplicate_keys(node: yaml.Node | None) -> None:
    """Fail on repeated mapping keys, which plain YAML loading silently collapses."""
    if isinstance(node, yaml.MappingNode):
        keys = [key.value for key, _ in node.value]
        repeated = sorted({str(key) for key in keys if keys.count(key) > 1})
        if repeated:
            where = "catalog"
            raise _invalid(where, f"repeats keys: {', '.join(repeated)}")
        for _, value in node.value:
            _reject_duplicate_keys(value)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _reject_duplicate_keys(item)


def _invalid(where: str, problem: str) -> CatalogError:
    return CatalogError(f"{where}: {problem}")
