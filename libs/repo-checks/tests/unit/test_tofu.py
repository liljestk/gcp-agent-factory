from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from repo_checks.encryption import check_encryption
from repo_checks.tofu_safety import check_tofu_safety

if TYPE_CHECKING:
    from pathlib import Path

CATALOG = """\
tiers: [canary]
stacks:
  demo:
    path: stacks/demo
    tier: canary
    envs: [dev]
    inputs: [config/shared/]
"""

ENCRYPTION = """\
terraform {
  encryption {
    key_provider "gcp_kms" "k" {
      kms_encryption_key = var.key
    }
    method "aes_gcm" "m" {
      keys = key_provider.gcp_kms.k
    }
    state {
      method   = method.aes_gcm.m
      enforced = true
    }
    plan {
      method   = method.aes_gcm.m
      enforced = true
    }
  }
}
"""


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safety(root: Path) -> list[str]:
    return [finding.render(root) for finding in check_tofu_safety(root)]


def encryption(root: Path) -> list[str]:
    return [finding.message for finding in check_encryption(root)]


def only(found: list[str], text: str) -> None:
    assert len(found) == 1, found
    assert text in found[0], found


class TestTofuSafetyDiscovery:
    def test_unparsable_files_are_findings(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf", "module {\n")
        assert safety(tmp_path) == ["stacks/demo/main.tf: [tofu-safety] isn't valid HCL"]

    def test_escaped_labels_are_findings(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf", 'data "ext\\u0065rnal" "x" {}\n')
        only(safety(tmp_path), "escape sequences aren't allowed in data block labels")

    def test_malformed_required_providers_are_findings(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf.json", '{"terraform": {"required_providers": "x"}}')
        only(safety(tmp_path), "required_providers blocks have an unexpected shape")

    def test_unparsable_lock_files_are_findings(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/.terraform.lock.hcl", "provider {\n")
        assert safety(tmp_path) == [
            "stacks/demo/.terraform.lock.hcl: [tofu-safety] isn't valid HCL"
        ]

    def test_allowed_lock_file_providers_pass(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/.terraform.lock.hcl",
            'provider "registry.opentofu.org/hashicorp/google" {\n  version = "7.0.0"\n}\n',
        )
        assert safety(tmp_path) == []

    def test_a_broken_catalog_declares_no_inputs(self, tmp_path: Path) -> None:
        write(tmp_path, "platforms/stacks.yaml", "tiers: [Bad]\n")
        write(tmp_path, "stacks/demo/main.tf", 'locals {\n  a = file("${path.module}/../x")\n}\n')
        only(safety(tmp_path), "file() reads 'stacks/x' outside its module")


class TestProviders:
    def test_non_literal_module_and_provider_sources_are_rejected(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'module "m" {\n  source = local.path\n}\n'
            "terraform {\n  required_providers {\n    google = {\n"
            "      source = var.provider\n    }\n  }\n}\n"
            'provider "google" {}\n',
        )
        assert safety(tmp_path) == [
            "stacks/demo/main.tf:6: [tofu-safety] provider google: source must be a literal string",
            "stacks/demo/main.tf:1: [tofu-safety] module m: source must be a literal local path",
        ]

    @pytest.mark.parametrize(
        ("spec", "problem"),
        [
            ('google = { version = "~> 7.0" }', None),
            ('random = "~> 3.0"', None),
            ('github = { source = "registry.terraform.io/Integrations/GitHub" }', None),
            ('aws = { version = "~> 6.0" }', "provider aws (hashicorp/aws)"),
        ],
        ids=["implied-allowed", "legacy-string", "registry-host-and-case", "implied-unlisted"],
    )
    def test_declared_sources_are_normalised(
        self,
        tmp_path: Path,
        spec: str,
        problem: str | None,
    ) -> None:
        body = f"terraform {{\n  required_providers {{\n    {spec}\n  }}\n}}\n"
        write(tmp_path, "stacks/demo/versions.tf", body)
        found = safety(tmp_path)
        if problem is None:
            assert found == []
        else:
            only(found, problem)

    def test_resource_types_resolve_through_required_providers_in_any_file(
        self,
        tmp_path: Path,
    ) -> None:
        write(
            tmp_path,
            "stacks/demo/versions.tf",
            "terraform {\n  required_providers {\n    github = {\n"
            '      source = "integrations/github"\n    }\n  }\n}\n',
        )
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'resource "github_repository" "r" {}\n'
            'resource "google_storage_bucket" "b" {\n  provider = google-beta.west\n}\n'
            'ephemeral "random_password" "p" {}\n',
        )
        assert safety(tmp_path) == []

    def test_the_provider_meta_argument_is_checked(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'resource "google_storage_bucket" "b" {\n  provider = evil.alias\n}\n',
        )
        only(safety(tmp_path), "uses provider hashicorp/evil")

    def test_provider_blocks(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/providers.tf",
            'provider "google" {\n  project = "p"\n  batching {\n'
            "    enable_batching = false\n  }\n}\n"
            'provider "github" {\n  owner    = "liljestk"\n'
            '  base_url = "https://example.com"\n}\n'
            'provider "aws" {}\n'
            "terraform {\n  required_providers {\n    github = {\n"
            '      source = "integrations/github"\n    }\n  }\n}\n',
        )
        assert safety(tmp_path) == [
            (
                'stacks/demo/providers.tf:1: [tofu-safety] provider "google" may not set batching: '
                "it could redirect CI's credentials"
            ),
            (
                'stacks/demo/providers.tf:7: [tofu-safety] provider "github" may not set base_url: '
                "it could redirect CI's credentials"
            ),
            (
                'stacks/demo/providers.tf:11: [tofu-safety] provider "aws" (hashicorp/aws) isn\'t '
                "on the provider allow-list (hashicorp/google, hashicorp/google-beta, "
                "hashicorp/random, integrations/github)"
            ),
        ]


class TestStateAndBlocks:
    @pytest.mark.parametrize(
        ("body", "problem"),
        [
            ('backend = "http"\n  config = {\n    bucket = "b"\n  }', 'must use backend = "gcs"'),
            ('backend = "gcs"\n  config  = local.config', "config must be an inline object"),
            ('backend = "gcs"\n  config = {\n    credentials = "x"\n  }', "not credentials"),
        ],
    )
    def test_remote_state_is_restricted(self, tmp_path: Path, body: str, problem: str) -> None:
        write(
            tmp_path, "stacks/demo/main.tf", f'data "terraform_remote_state" "r" {{\n  {body}\n}}\n'
        )
        only(safety(tmp_path), problem)

    def test_backends_and_cloud_blocks_are_restricted(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'terraform {\n  backend "gcs" {\n    bucket = "b"\n    access_token = "x"\n  }\n'
            '  cloud {\n    organization = "o"\n  }\n}\n',
        )
        assert safety(tmp_path) == [
            (
                "stacks/demo/main.tf: [tofu-safety] a cloud block sends state and runs elsewhere; "
                "use the gcs backend"
            ),
            (
                'stacks/demo/main.tf:2: [tofu-safety] backend "gcs" may only set bucket and '
                "prefix, not access_token"
            ),
        ]

    @pytest.mark.parametrize(
        "kind",
        [
            "google_secret_manager_secret_version_access",
            "google_secret_manager_regional_secret_version",
            "google_kms_secret",
            "google_service_account_access_token",
        ],
    )
    def test_secret_payload_types_are_rejected(self, tmp_path: Path, kind: str) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            f'data "{kind}" "s" {{}}\ndata "google_project" "p" {{}}\n',
        )
        only(safety(tmp_path), f'data "{kind}" handles a secret payload')

    def test_provisioners_are_found_at_any_depth(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            "removed {\n  from = terraform_data.x\n"
            '  provisioner "local-exec" {\n    when    = destroy\n    command = "id"\n  }\n}\n',
        )
        assert safety(tmp_path) == [
            (
                "stacks/demo/main.tf:3: [tofu-safety] provisioners run commands on the runner and "
                "aren't allowed"
            ),
        ]

    @pytest.mark.parametrize(
        ("source", "problem"),
        [
            ("./build", "is inside build/, which the checks skip"),
            ("../../modules/dist/x", "is inside dist/, which the checks skip"),
            ("../../../../outside", "leaves the repository"),
        ],
    )
    def test_module_sources_must_stay_checkable(
        self,
        tmp_path: Path,
        source: str,
        problem: str,
    ) -> None:
        write(tmp_path, "stacks/demo/main.tf", f'module "m" {{\n  source = "{source}"\n}}\n')
        only(safety(tmp_path), problem)


class TestJsonAndTemplates:
    def test_json_configurations_are_checked_too(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf.json",
            "{\n"
            '  "data": {"external": {"x": {}}},\n'
            '  "resource": {"terraform_data": {"y": {"provisioner": {"local-exec": {}}}}},\n'
            '  "module": {"m": {"source": "git::https://example.com/m.git"}},\n'
            '  "locals": {"c": "${file(\\"x\\")}"}\n'
            "}\n",
        )
        found = safety(tmp_path)
        assert [line.split(" [tofu-safety] ")[0] for line in found] == [
            "stacks/demo/main.tf.json:2:",
            "stacks/demo/main.tf.json:3:",
            "stacks/demo/main.tf.json:4:",
            "stacks/demo/main.tf.json:5:",
        ]
        assert "hashicorp/external" in found[0]
        assert "provisioners run commands" in found[1]
        assert "isn't a local path" in found[2]
        assert "can't be checked in JSON syntax" in found[3]

    def test_json_unicode_escapes_are_rejected(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf.json",
            '{\n  "output": {"o": {"value": "${nonsens\\u0069tive(var.x)}"}}\n}\n',
        )
        assert safety(tmp_path) == [
            (
                "stacks/demo/main.tf.json:2: [tofu-safety] \\u escapes aren't allowed in OpenTofu "
                "JSON: they can hide calls"
            ),
        ]

    def test_clean_templates_pass(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/templates/a.tpl", "Hello ${name}\n")
        assert safety(tmp_path) == []


class TestFileReads:
    @pytest.mark.parametrize(
        ("call", "problem"),
        [
            ('fileset(path.module, "templates/*.tftpl")', None),
            ('fileset("${path.module}/templates", "*.tftpl")', None),
            ('fileset(path.module, "../*")', "fileset() patterns must be literal"),
            ('fileset("${path.module}/sub", "../../../*")', "fileset() patterns must be literal"),
            ("fileset(path.module, var.pattern)", "fileset() patterns must be literal"),
            (
                'fileset(path.module, "%{if true}..%{endif}/*")',
                "fileset() patterns must be literal",
            ),
            ("file(path.module)", "must read a literal path under"),
            ("templatefile(var.template, {})", "must read a literal path under"),
            ('file("relative.txt")', "must read a literal path under"),
            ('file("${path.module}/${var.name}.yaml")', "must read a literal path under"),
            ('file("${path.module}/%{if true}../..%{endif}/x")', "must read a literal path under"),
            ('file("${path.module}/\\u002e\\u002e/x")', "must read a literal path under"),
            ('file("${path.module}/files/ok.txt")', None),
            ('file("${path.module}/../../config/shared/a.yaml")', None),
            ('fileset("${path.module}/../../config/shared", "*.yaml")', None),
            ('file("${path.module}/../../../../outside")', "reads a path outside the repository"),
        ],
    )
    def test_file_reads(self, tmp_path: Path, call: str, problem: str | None) -> None:
        write(tmp_path, "platforms/stacks.yaml", CATALOG)
        write(tmp_path, "stacks/demo/main.tf", f"locals {{\n  value = {call}\n}}\n")
        found = safety(tmp_path)
        if problem is None:
            assert found == []
        else:
            only(found, problem)

    def test_declared_file_inputs_match_exactly(self, tmp_path: Path) -> None:
        write(
            tmp_path, "platforms/stacks.yaml", CATALOG.replace("config/shared/", "config/demo.yaml")
        )
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'locals {\n  a = file("${path.module}/../../config/demo.yaml")\n'
            '  b = file("${path.module}/../../config/demo.yaml.bak")\n}\n',
        )
        assert safety(tmp_path) == [
            (
                "stacks/demo/main.tf:3: [tofu-safety] file() reads 'config/demo.yaml.bak' outside "
                "its module; declare it in the stack's inputs"
            ),
        ]


class TestEncryption:
    def test_a_compliant_root_module_passes(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/backend.tf", 'terraform {\n  backend "gcs" {}\n}\n')
        write(tmp_path, "stacks/demo/encryption.tf", ENCRYPTION)
        assert encryption(tmp_path) == []

    def test_unparsable_catalog_stacks_are_findings(self, tmp_path: Path) -> None:
        write(tmp_path, "platforms/stacks.yaml", CATALOG)
        write(tmp_path, "stacks/demo/main.tf", "module {\n")
        assert encryption(tmp_path) == ["stacks/demo/main.tf: isn't valid HCL"]

    def test_a_broken_catalog_still_finds_backends(self, tmp_path: Path) -> None:
        write(tmp_path, "platforms/stacks.yaml", "tiers: [Bad]\n")
        write(tmp_path, "stacks/demo/main.tf.json", '{"terraform": {"backend": {"gcs": {}}}}')
        assert encryption(tmp_path) == [
            "root module has no `encryption` block; state and plans must be encrypted (ADR-0011)",
        ]

    def test_identifier_backend_labels_count(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf", "terraform {\n  backend gcs {}\n}\n")
        assert len(encryption(tmp_path)) == 1

    def test_override_files_cannot_change_the_backend(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf", ENCRYPTION)
        write(tmp_path, "stacks/demo/override.tf", 'terraform {\n  backend "gcs" {}\n}\n')
        assert encryption(tmp_path) == [
            "stacks/demo/override.tf: override files may not change the backend"
        ]

    def test_exactly_one_encryption_block(self, tmp_path: Path) -> None:
        write(tmp_path, "stacks/demo/main.tf", 'terraform {\n  backend "gcs" {}\n}\n' + ENCRYPTION)
        write(tmp_path, "stacks/demo/second.tf", ENCRYPTION)
        assert encryption(tmp_path) == ["a root module must have exactly one `encryption` block"]

    def test_every_part_is_validated(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'terraform {\n  backend "gcs" {}\n  encryption {\n'
            '    key_provider "gcp_kms" "k" {}\n'
            '    method "aes_gcm" "wrong" {\n      keys = key_provider.gcp_kms.other\n    }\n'
            '    method "aes_gcm" "m" {\n      keys = key_provider.gcp_kms.k\n    }\n'
            "    state {\n      method   = method.aes_gcm.wrong\n      enforced = true\n    }\n"
            "  }\n}\n",
        )
        assert encryption(tmp_path) == [
            'method "aes_gcm" "wrong" must take its keys from a gcp_kms key provider',
            "the state block must use an aes_gcm method and set `enforced = true`",
            "the plan block must use an aes_gcm method and set `enforced = true`",
        ]

    def test_missing_key_providers_are_reported(self, tmp_path: Path) -> None:
        write(
            tmp_path,
            "stacks/demo/main.tf",
            'terraform {\n  backend "gcs" {}\n  encryption {}\n}\n',
        )
        assert encryption(tmp_path)[0] == (
            "key providers must be `gcp_kms`: a passphrase in a public repository is no key"
        )
