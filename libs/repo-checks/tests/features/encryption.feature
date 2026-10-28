@REQ-LZ-003
Feature: Every root module encrypts its state and plans
  ADR-0011: state and saved plans are encrypted with a KMS key before they
  leave the runner. A root module is a directory with a backend block or a
  stack in the catalog. Each needs exactly one encryption block with a
  gcp_kms key provider and an aes_gcm method, enforced for state and plans,
  and without a fallback. Files are read the way OpenTofu reads them.

  Background:
    Given a file "stacks/demo/backend.tf" containing:
      """
      terraform {
        backend "gcs" {}
      }
      """

  Scenario: KMS encryption enforced for state and plans passes
    Given a file "stacks/demo/encryption.tf" containing:
      """
      terraform {
        encryption {
          key_provider "gcp_kms" "state" {
            kms_encryption_key = var.state_key
            key_length         = 32
          }
          method "aes_gcm" "state" {
            keys = key_provider.gcp_kms.state
          }
          state {
            method   = method.aes_gcm.state
            enforced = true
          }
          plan {
            method   = method.aes_gcm.state
            enforced = true
          }
        }
      }
      """
    When I run the "encryption" check
    Then no findings are reported

  Scenario: A root module without an encryption block fails
    When I run the "encryption" check
    Then a finding for "stacks/demo" mentions "no `encryption` block"

  Scenario: Encryption that plans can bypass fails
    Given a file "stacks/demo/encryption.tf" containing:
      """
      terraform {
        encryption {
          key_provider "gcp_kms" "state" {
            kms_encryption_key = var.state_key
          }
          method "aes_gcm" "state" {
            keys = key_provider.gcp_kms.state
          }
          state {
            method   = method.aes_gcm.state
            enforced = true
          }
          plan {
            method   = method.aes_gcm.state
            enforced = false
          }
        }
      }
      """
    When I run the "encryption" check
    Then a finding for "stacks/demo" mentions "the plan block must use an aes_gcm method"

  Scenario: A passphrase and a fallback fail
    Given a file "stacks/demo/encryption.tf" containing:
      """
      terraform {
        encryption {
          key_provider "pbkdf2" "state" {
            passphrase = "correct-horse-battery-staple"
          }
          method "aes_gcm" "state" {
            keys = key_provider.pbkdf2.state
          }
          method "unencrypted" "migrate" {}
          state {
            method   = method.aes_gcm.state
            enforced = true
            fallback {
              method = method.unencrypted.migrate
            }
          }
          plan {
            method   = method.aes_gcm.state
            enforced = true
          }
        }
      }
      """
    When I run the "encryption" check
    Then a finding for "stacks/demo" mentions "key providers must be `gcp_kms`"
    And a finding for "stacks/demo" mentions "`fallback` would accept state"
    And a finding for "stacks/demo" mentions "isn't allowed; use aes_gcm"

  Scenario: A .tofu file shadows the .tf file of the same name
    Given a file "stacks/demo/encryption.tf" containing:
      """
      terraform {
        encryption {
          key_provider "gcp_kms" "state" {}
        }
      }
      """
    And a file "stacks/demo/encryption.tofu" containing:
      """
      # OpenTofu loads this file instead of encryption.tf
      """
    When I run the "encryption" check
    Then a finding for "stacks/demo" mentions "no `encryption` block"

  Scenario: Override files can't change encryption
    Given a file "stacks/demo/encryption_override.tf" containing:
      """
      terraform {
        encryption {}
      }
      """
    When I run the "encryption" check
    Then a finding for "stacks/demo" mentions "override files may not change encryption"

  Scenario: A stack in the catalog is a root module before it has a backend
    Given a file "platforms/stacks.yaml" containing:
      """
      tiers: [canary]
      stacks:
        later:
          path: stacks/later
          tier: canary
          envs: [dev]
      """
    And a file "stacks/later/main.tf" containing:
      """
      # nothing here yet
      """
    When I run the "encryption" check
    Then a finding for "stacks/later" mentions "no `encryption` block"

  Scenario: Reusable modules are not root modules
    Given a file "modules/demo/main.tf" containing:
      """
      variable "name" {
        type = string
      }
      """
    When I run the "encryption" check
    Then no findings are reported for "modules/demo"

  Scenario: The repository's root modules are encrypted
    Given the gcp-agent-factory repository
    When I run the "encryption" check
    Then no findings are reported
