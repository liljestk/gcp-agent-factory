terraform {
  required_version = ">= 1.13.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.7"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # Trust-root state, written only by the owner (ADR-0018). The first run starts on a local
  # backend with a passphrase override and then migrates here (docs/runbooks/bootstrap.md).
  backend "gcs" {
    bucket = var.state_bucket
    prefix = "trust-root/bootstrap"
  }

  encryption {
    key_provider "gcp_kms" "trust_root" {
      kms_encryption_key = var.state_key
      key_length         = 32
    }

    method "aes_gcm" "trust_root" {
      keys = key_provider.gcp_kms.trust_root
    }

    state {
      method   = method.aes_gcm.trust_root
      enforced = true
    }

    plan {
      method   = method.aes_gcm.trust_root
      enforced = true
    }
  }
}

provider "google" {
  region = var.region

  # API quota is charged to the seed. With user credentials, budgets, org policies and deny
  # policies refuse calls without a quota project, and the provider ignores the one in the ADC
  # file. So the first run applies the seed alone, then everything with quota_project set to it.
  billing_project       = var.quota_project
  user_project_override = var.quota_project != null
}
