"""Checks that every root module encrypts its state and plans (REQ-LZ-003, ADR-0011).

Encryption must use a ``gcp_kms`` key provider and an ``aes_gcm`` method, be enforced for
state and plans, and have no ``fallback``: a passphrase in a public repository is no key, and a
fallback would accept unencrypted state. Files are read the way OpenTofu reads them, and
override files may not change encryption or the backend.
"""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, Final

from repo_checks.files import iter_files
from repo_checks.findings import Finding
from stacks.catalog import CATALOG_PATH, CatalogError, load_catalog
from stacks.errors import StacksError
from stacks.hcl import CONFIG_SUFFIXES, config_paths, contains_key, is_override, load_config

if TYPE_CHECKING:
    from pathlib import Path

    from stacks.hcl import ConfigFile

CHECK = "encryption"
TARGETS: Final = ("state", "plan")
KEY_REFERENCE: Final = re.compile(r"^\$\{key_provider\.gcp_kms\.([A-Za-z0-9_-]+)\}$")
METHOD_REFERENCE: Final = re.compile(r"^\$\{method\.aes_gcm\.([A-Za-z0-9_-]+)\}$")
MISSING: Final = (
    "root module has no `encryption` block; state and plans must be encrypted (ADR-0011)"
)


def check_encryption(root: Path) -> list[Finding]:
    """Root modules encrypt state and plans with a KMS key, enforced and without fallback.

    A root module is a directory with a ``backend`` block, or a stack in the catalog.
    """
    return [
        Finding(CHECK, root / directory, problem)
        for directory in _root_modules(root)
        for problem in _problems(root, directory)
    ]


def _root_modules(root: Path) -> list[str]:
    directories: set[str] = set()
    for path in iter_files(root, CONFIG_SUFFIXES):
        # tofu-safety reports files that can't be parsed; here they just aren't evidence.
        with contextlib.suppress(StacksError):
            config = load_config(path, path.relative_to(root).as_posix())
            if any(
                config.blocks_in(body, "backend", 1) for _, body in config.blocks("terraform", 0)
            ):
                directories.add(path.parent.relative_to(root).as_posix())
    catalog = root / CATALOG_PATH
    if catalog.is_file():
        # `stacks validate` reports a broken catalog; the backend scan still finds the stacks.
        with contextlib.suppress(CatalogError):
            directories |= {
                stack.path for stack in load_catalog(catalog).stacks if (root / stack.path).is_dir()
            }
    return sorted(directories)


def _problems(root: Path, directory: str) -> list[str]:
    try:
        configs = [
            load_config(path, f"{directory}/{path.name}") for path in config_paths(root / directory)
        ]
        return _encryption_problems(configs)
    except StacksError as error:
        return [str(error)]


def _encryption_problems(configs: list[ConfigFile]) -> list[str]:
    problems: list[str] = []
    blocks: list[tuple[ConfigFile, dict[str, object]]] = []
    for config in configs:
        override = is_override(config.where.rpartition("/")[2])
        for _, terraform in config.blocks("terraform", 0):
            found = config.blocks_in(terraform, "encryption", 0)
            if override and found:
                problems.append(f"{config.where}: override files may not change encryption")
            if override and config.blocks_in(terraform, "backend", 1):
                problems.append(f"{config.where}: override files may not change the backend")
            blocks += [(config, body) for _, body in found]
    if not blocks:
        return [*problems, MISSING]
    if len(blocks) > 1:
        return [*problems, "a root module must have exactly one `encryption` block"]
    config, encryption = blocks[0]
    return [*problems, *_settings_problems(config, encryption)]


def _settings_problems(config: ConfigFile, encryption: dict[str, object]) -> list[str]:
    problems: list[str] = []
    if contains_key(encryption, "fallback"):
        problems.append(
            "`fallback` would accept state that isn't KMS-encrypted; "
            "migrate with a local TF_ENCRYPTION override instead",
        )
    keys = config.blocks_in(encryption, "key_provider", 2)
    if not keys or any(kind != "gcp_kms" for (kind, _), _ in keys):
        problems.append(
            "key providers must be `gcp_kms`: a passphrase in a public repository is no key"
        )
    key_names = {name for (kind, name), _ in keys if kind == "gcp_kms"}
    method_names: set[str] = set()
    for (kind, name), body in config.blocks_in(encryption, "method", 2):
        reference = KEY_REFERENCE.match(str(body.get("keys", "")))
        if kind != "aes_gcm":
            problems.append(f'method "{kind}" isn\'t allowed; use aes_gcm')
        elif reference is None or reference.group(1) not in key_names:
            problems.append(
                f'method "aes_gcm" "{name}" must take its keys from a gcp_kms key provider'
            )
        else:
            method_names.add(name)
    for target in TARGETS:
        found = config.blocks_in(encryption, target, 0)
        settings = found[0][1] if len(found) == 1 else {}
        reference = METHOD_REFERENCE.match(str(settings.get("method", "")))
        if (
            settings.get("enforced") is not True
            or reference is None
            or reference.group(1) not in method_names
        ):
            problems.append(
                f"the {target} block must use an aes_gcm method and set `enforced = true`"
            )
    return problems
