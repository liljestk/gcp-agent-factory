"""Checks that stack code can't leak data through a plan (REQ-LZ-012).

Plans run code from pull requests with CI's credentials, and their output is public. So OpenTofu
code may only use allow-listed providers, configured so they can't be pointed at another
endpoint, and state may only live in the gcs backend. It also may not run commands, print
sensitive values, use remote modules, handle secret payloads, or read files the stack matrix
doesn't know about.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final

from repo_checks.files import IGNORED_DIRS, iter_files
from repo_checks.findings import Finding
from stacks.catalog import CATALOG_PATH, CatalogError, load_catalog
from stacks.errors import StacksError
from stacks.hcl import CONFIG_SUFFIXES, contains_key, load_config
from stacks.modules import LOCAL_PREFIXES, join_path

if TYPE_CHECKING:
    from pathlib import Path

    from stacks.hcl import ConfigFile

CHECK = "tofu-safety"
LOCK_FILE: Final = ".terraform.lock.hcl"
TEMPLATE_SUFFIXES: Final = (".tftpl", ".tpl")
BUILTIN: Final = "terraform"  # terraform_data and terraform_remote_state need no provider
REGISTRY_HOSTS: Final = ("registry.opentofu.org/", "registry.terraform.io/")
GOOGLE_ARGUMENTS: Final = frozenset(
    {
        "alias",
        "project",
        "region",
        "zone",
        "billing_project",
        "user_project_override",
        "default_labels",
        "add_terraform_attribution_label",
        "request_timeout",
    },
)
# The allow-list: provider source -> the arguments its provider blocks may set. Anything else
# (custom endpoints, credentials, base URLs) could send CI's credentials somewhere else.
PROVIDERS: Final = {
    "hashicorp/google": GOOGLE_ARGUMENTS,
    "hashicorp/google-beta": GOOGLE_ARGUMENTS,
    "hashicorp/random": frozenset({"alias"}),
    "integrations/github": frozenset({"alias", "owner"}),
}
BACKEND_ARGUMENTS: Final = frozenset({"bucket", "prefix"})
TYPED_BLOCKS: Final = ("resource", "data", "ephemeral")
SECRET_TYPES: Final = re.compile(
    r"^google_(secret_manager_(regional_)?secret_version(_access)?|kms_secret\w*"
    r"|service_account_(key|access_token|id_token|jwt))$",
)
NONSENSITIVE: Final = re.compile(r"\bnonsensitive\s*\(")
FILE_FUNCTIONS: Final = (
    "file",
    "filebase64",
    "filebase64sha256",
    "filebase64sha512",
    "fileexists",
    "filemd5",
    "filesha1",
    "filesha256",
    "filesha512",
    "fileset",
    "templatefile",
)
FILE_CALL: Final = re.compile(rf"\b({'|'.join(FILE_FUNCTIONS)})\s*\(\s*")
MODULE_PATH: Final = '"${path.module}/'
UNSAFE_PATH: Final = ("${", "%{", "\\")
JSON_ESCAPE: Final = re.compile(r"\\u")

Problem = tuple[str, int | None]


def check_tofu_safety(root: Path) -> list[Finding]:
    """OpenTofu code can't send data out, run commands or put secrets into state or plans."""
    inputs = _declared_inputs(root)
    findings: list[Finding] = []
    directories: dict[Path, list[ConfigFile]] = defaultdict(list)
    for path in iter_files(root, CONFIG_SUFFIXES):
        where = path.relative_to(root).as_posix()
        try:
            directories[path.parent].append(load_config(path, where))
        except StacksError as error:
            findings.append(Finding(CHECK, path, _message(error, where)))
    for directory in sorted(directories):
        findings.extend(_directory_findings(root, directories[directory], inputs))
    for path in iter_files(root, (LOCK_FILE,)):
        where = path.relative_to(root).as_posix()
        try:
            problems = _lock_problems(load_config(path, where))
        except StacksError as error:
            problems = [(_message(error, where), None)]
        findings.extend(Finding(CHECK, path, message, line) for message, line in problems)
    for path in iter_files(root, TEMPLATE_SUFFIXES):
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(
            Finding(CHECK, path, message, line) for message, line in _template_problems(text)
        )
    return findings


def _declared_inputs(root: Path) -> tuple[str, ...]:
    catalog = root / CATALOG_PATH
    if not catalog.is_file():
        return ()
    try:
        stacks = load_catalog(catalog).stacks
    except CatalogError:
        # `stacks validate` reports a broken catalog; until it's fixed, nothing is declared.
        return ()
    return tuple(entry for stack in stacks for entry in stack.inputs)


def _directory_findings(
    root: Path,
    configs: list[ConfigFile],
    inputs: tuple[str, ...],
) -> list[Finding]:
    """Check one module directory; ``required_providers`` may sit in any of its files."""
    findings: list[Finding] = []
    providers: dict[str, str | None] = {}
    readable: list[ConfigFile] = []
    for config in configs:
        try:
            providers.update(_required_providers(config))
            readable.append(config)
        except StacksError as error:
            findings.append(Finding(CHECK, root / config.where, _message(error, config.where)))
    for config in readable:
        try:
            problems = [
                *_declaration_problems(config),
                *_typed_block_problems(config, providers),
                *_provider_block_problems(config, providers),
                *_backend_problems(config),
                *_provisioner_problems(config),
                *_module_problems(config),
                *_text_problems(config, inputs),
            ]
        except StacksError as error:
            problems = [(_message(error, config.where), None)]
        findings.extend(Finding(CHECK, root / config.where, msg, line) for msg, line in problems)
    return findings


def _required_providers(config: ConfigFile) -> dict[str, str | None]:
    """Map each provider local name to its literal source, or ``None`` if it isn't literal."""
    return {
        name: (
            config.literal(spec["source"])
            if isinstance(spec, dict) and "source" in spec
            else f"hashicorp/{name}"
        )
        for _, terraform in config.blocks("terraform", 0)
        for _, declared in config.blocks_in(terraform, "required_providers", 0)
        for name, spec in declared.items()
    }


def _declaration_problems(config: ConfigFile) -> list[Problem]:
    problems: list[Problem] = []
    for name, source in _required_providers(config).items():
        if source is None:
            line = config.line_of(_label(config, name, ""))
            problems.append((f"provider {name}: source must be a literal string", line))
        elif _provider(source) not in PROVIDERS:
            problems.append(
                (_unlisted(f"provider {name} ({source})"), config.line_of(re.escape(source)))
            )
    return problems


def _typed_block_problems(config: ConfigFile, providers: dict[str, str | None]) -> list[Problem]:
    """Every resource, data and ephemeral block, including data blocks inside ``check``."""
    blocks = [
        (kind, labels, body) for kind in TYPED_BLOCKS for labels, body in config.blocks(kind, 2)
    ]
    blocks += [
        ("data", labels, body)
        for _, check in config.blocks("check", 1)
        for labels, body in config.blocks_in(check, "data", 2)
    ]
    problems: list[Problem] = []
    for kind, (type_, _), body in blocks:
        line = config.line_of(_label(config, kind, type_))
        if SECRET_TYPES.match(type_):
            problems.append(
                (f'{kind} "{type_}" handles a secret payload a plan would expose', line)
            )
        local = _local_provider(type_, body)
        if local == BUILTIN:
            if type_ == "terraform_remote_state":
                problems.extend((problem, line) for problem in _remote_state_problems(config, body))
            continue
        source = providers.get(local, f"hashicorp/{local}")
        if source is not None and _provider(source) not in PROVIDERS:
            problems.append((_unlisted(f'{kind} "{type_}" uses provider {source}, which'), line))
    return problems


def _local_provider(type_: str, body: dict[str, object]) -> str:
    """The provider local name: the ``provider`` meta-argument, else the type's prefix."""
    meta = body.get("provider")
    if isinstance(meta, str):
        return meta.removeprefix("${").removesuffix("}").split(".", 1)[0]
    return type_.split("_", 1)[0]


def _remote_state_problems(config: ConfigFile, body: dict[str, object]) -> list[str]:
    problems: list[str] = []
    if config.literal(body.get("backend")) != "gcs":
        problems.append('terraform_remote_state must use backend = "gcs"')
    settings = body.get("config")
    if not isinstance(settings, dict):
        problems.append("terraform_remote_state config must be an inline object")
    elif extra := sorted({str(key).strip('"') for key in settings} - BACKEND_ARGUMENTS):
        problems.append(
            f"terraform_remote_state config may only set bucket and prefix, not {', '.join(extra)}"
        )
    return problems


def _provider_block_problems(config: ConfigFile, providers: dict[str, str | None]) -> list[Problem]:
    problems: list[Problem] = []
    for (local,), body in config.blocks("provider", 1):
        line = config.line_of(_label(config, "provider", local))
        source = providers.get(local, f"hashicorp/{local}")
        if source is None:
            continue  # reported with the required_providers entry
        allowed = PROVIDERS.get(_provider(source))
        if allowed is None:
            problems.append((_unlisted(f'provider "{local}" ({source})'), line))
        elif extra := sorted(set(body) - allowed):
            message = f'provider "{local}" may not set {", ".join(extra)}: it could redirect CI'
            problems.append((f"{message}'s credentials", line))
    return problems


def _backend_problems(config: ConfigFile) -> list[Problem]:
    problems: list[Problem] = []
    for _, terraform in config.blocks("terraform", 0):
        if "cloud" in terraform:
            problems.append(
                ("a cloud block sends state and runs elsewhere; use the gcs backend", None)
            )
        for (name,), body in config.blocks_in(terraform, "backend", 1):
            line = config.line_of(_label(config, "backend", ""))
            if name != "gcs":
                problems.append(
                    (f'backend "{name}" isn\'t allowed; state lives in the gcs backend', line)
                )
            elif extra := sorted(set(body) - BACKEND_ARGUMENTS):
                problems.append(
                    (f'backend "gcs" may only set bucket and prefix, not {", ".join(extra)}', line)
                )
    return problems


def _provisioner_problems(config: ConfigFile) -> list[Problem]:
    if not contains_key(config.document, "provisioner"):
        return []
    line = config.line_of(_label(config, "provisioner", ""))
    return [("provisioners run commands on the runner and aren't allowed", line)]


def _module_problems(config: ConfigFile) -> list[Problem]:
    directory = config.where.rpartition("/")[0]
    problems: list[Problem] = []
    for (name,), body in config.blocks("module", 1):
        source = config.literal(body.get("source"))
        line = config.line_of(_label(config, "module", name))
        if source is None:
            problems.append((f"module {name}: source must be a literal local path", line))
            continue
        if not source.startswith(LOCAL_PREFIXES):
            problems.append((f"module {name}: source {source!r} isn't a local path", line))
            continue
        target = join_path(directory, source)
        if target is None:
            problems.append((f"module {name}: source {source!r} leaves the repository", line))
        elif skipped := sorted(IGNORED_DIRS & set(target.split("/"))):
            message = f"module {name}: source {source!r} is inside {skipped[0]}/"
            problems.append((f"{message}, which the checks skip", line))
    return problems


def _text_problems(config: ConfigFile, inputs: tuple[str, ...]) -> list[Problem]:
    directory = config.where.rpartition("/")[0]
    problems: list[Problem] = []
    if config.json_syntax and JSON_ESCAPE.search(config.text):
        line = config.line_of(JSON_ESCAPE.pattern)
        problems.append(("\\u escapes aren't allowed in OpenTofu JSON: they can hide calls", line))
    problems += [
        ("nonsensitive() would print a sensitive value in a public plan", _line(config.text, start))
        for start in (match.start() for match in NONSENSITIVE.finditer(config.text))
    ]
    for match in FILE_CALL.finditer(config.text):
        problem = _file_call_problem(config, match, directory, inputs)
        if problem is not None:
            problems.append((problem, _line(config.text, match.start())))
    return problems


def _file_call_problem(
    config: ConfigFile,
    match: re.Match[str],
    directory: str,
    inputs: tuple[str, ...],
) -> str | None:
    """Files a stack reads must sit in its module directory or be declared in ``inputs``.

    Otherwise the stack matrix can't see that a change to them affects the stack.
    """
    function = match.group(1)
    if config.json_syntax:
        return f"{function}() can't be checked in JSON syntax; read files from HCL"
    argument = _path_argument(config.text[match.end() :], function, directory)
    if argument is None:
        return f"{function}() must read a literal path under ${{path.module}}/"
    base, after = argument
    if function == "fileset" and not _safe_pattern(after):
        return "fileset() patterns must be literal and stay inside the base directory"
    if base is None:
        return f"{function}() reads a path outside the repository"
    inside = base == directory or base.startswith(f"{directory}/")
    if inside or any(_matches(base, entry) for entry in inputs):
        return None
    return f"{function}() reads {base!r} outside its module; declare it in the stack's inputs"


def _path_argument(rest: str, function: str, directory: str) -> tuple[str | None, str] | None:
    """Read the first argument of a file function.

    Returns ``(base, remaining text)``, where ``base`` is the repo-relative path (``None`` if
    it leaves the repository), or ``None`` if the argument isn't a literal path under
    ``${path.module}/`` (or a bare ``path.module`` for ``fileset``).
    """
    if function == "fileset" and rest.startswith("path.module"):
        return directory, rest.removeprefix("path.module")
    if not rest.startswith(MODULE_PATH):
        return None
    # The file parsed as HCL, so the string that opens here also closes.
    relative = rest[len(MODULE_PATH) : rest.find('"', len(MODULE_PATH))]
    if any(marker in relative for marker in UNSAFE_PATH):
        return None
    return join_path(directory, relative), rest[len(MODULE_PATH) + len(relative) + 1 :]


def _safe_pattern(arguments: str) -> bool:
    """The second ``fileset()`` argument is a literal glob that can't climb out of the base."""
    pattern = _first_string(arguments.lstrip(" ,\t\r\n"))
    return (
        pattern is not None
        and not any(marker in pattern for marker in UNSAFE_PATH)
        and ".." not in PurePosixPath(pattern).parts
    )


def _template_problems(text: str) -> list[Problem]:
    """Templates can call functions too, so they may not print secrets or read other files."""
    problems: list[Problem] = [
        ("templates can't call nonsensitive()", _line(text, match.start()))
        for match in NONSENSITIVE.finditer(text)
    ]
    problems += [
        (f"templates can't call {match.group(1)}()", _line(text, match.start()))
        for match in FILE_CALL.finditer(text)
    ]
    return problems


def _lock_problems(config: ConfigFile) -> list[Problem]:
    return [
        (_unlisted(f"provider {address}"), config.line_of(re.escape(f'"{address}"')))
        for (address,), _ in config.blocks("provider", 1)
        if _provider(address) not in PROVIDERS
    ]


def _first_string(text: str) -> str | None:
    """Return the string literal ``text`` starts with; it closes because the file parsed."""
    return text[1 : text.find('"', 1)] if text.startswith('"') else None


def _matches(path: str, entry: str) -> bool:
    prefix = entry.removesuffix("/")
    return path == prefix or path.startswith(f"{prefix}/")


def _provider(source: str) -> str:
    normalised = source.lower()
    for host in REGISTRY_HOSTS:
        normalised = normalised.removeprefix(host)
    return normalised


def _unlisted(what: str) -> str:
    allowed = ", ".join(sorted(PROVIDERS))
    return f"{what} isn't on the provider allow-list ({allowed})"


def _label(config: ConfigFile, block: str, label: str) -> str:
    """Regex for the line that opens ``block "label"`` (HCL) or the ``"label":`` key (JSON)."""
    if config.json_syntax:
        return rf'"{re.escape(label or block)}"\s*:'
    return rf'\b{re.escape(block)}\s+"{re.escape(label)}' if label else rf"\b{re.escape(block)}\b"


def _line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _message(error: StacksError, where: str) -> str:
    return str(error).removeprefix(f"{where}: ")
