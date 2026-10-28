variable "org_id" {
  description = "Numeric ID of the organization (ADR-0017). It identifies but doesn't authorize."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{6,20}$", var.org_id))
    error_message = "org_id must be the numeric organization ID."
  }
}

variable "customer_id" {
  description = "Directory customer ID of the Google account, e.g. C01abcd2e. Later stacks key the domain restriction on it."
  type        = string

  validation {
    condition     = can(regex("^C[0-9a-z]{6,12}$", var.customer_id))
    error_message = "customer_id must look like C01abcd2e."
  }
}

variable "identity_domain" {
  description = "Domain of the platform's groups (ADR-0017). Group addresses derive from it, e.g. gcp-org-admins@<domain>."
  type        = string

  validation {
    condition     = can(regex("^([a-z0-9]([a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,}$", var.identity_domain))
    error_message = "identity_domain must be a lowercase domain name such as example.com."
  }
}

variable "billing_account" {
  description = "ID of the billing account the seed links to and the budget watches, e.g. 012345-6789AB-CDEF01."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}$", var.billing_account))
    error_message = "billing_account must look like 012345-6789AB-CDEF01."
  }
}

variable "region" {
  description = "Region of the key ring and the state bucket. A key's location can never change."
  type        = string
  default     = "europe-north1"

  validation {
    condition     = can(regex("^europe-[a-z]+[0-9]+$", var.region))
    error_message = "region must be a European region such as europe-north1."
  }
}

variable "repository" {
  description = "GitHub repository as owner/name. It pins only the apply workflow; trust is pinned by IDs."
  type        = string
  default     = "liljestk/gcp-agent-factory"

  validation {
    condition     = can(regex("^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$", var.repository))
    error_message = "repository must look like owner/name."
  }
}

variable "repository_id" {
  description = "Immutable numeric ID of the repository; the only one whose tokens are accepted (REQ-LZ-001)."
  type        = string
  default     = "1431415117"

  validation {
    condition     = can(regex("^[0-9]+$", var.repository_id))
    error_message = "repository_id must be the numeric repository ID."
  }
}

variable "repository_owner_id" {
  description = "Immutable numeric ID of the repository owner, whose pull requests may plan."
  type        = string
  default     = "4373495"

  validation {
    condition     = can(regex("^[0-9]+$", var.repository_owner_id))
    error_message = "repository_owner_id must be the numeric owner ID."
  }
}

variable "state_bucket" {
  description = "State bucket this stack's own state lives in (early-evaluated, for the backend). Null only on the first, local run."
  type        = string
  default     = null

  validation {
    condition     = var.state_bucket == null || can(regex("^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$", coalesce(var.state_bucket, "-")))
    error_message = "state_bucket must be a bucket name."
  }
}

variable "state_key" {
  description = "ID of the trust-root state key that encrypts this stack's state and plans (early-evaluated). Null only on the first, local run, when a passphrase override encrypts instead; without one, OpenTofu refuses to write state."
  type        = string
  default     = null

  validation {
    condition     = var.state_key == null || can(regex("^projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/locations/[a-z0-9-]+/keyRings/[A-Za-z0-9_-]+/cryptoKeys/[A-Za-z0-9_-]+$", coalesce(var.state_key, "-")))
    error_message = "state_key must be a crypto key ID: projects/<p>/locations/<l>/keyRings/<r>/cryptoKeys/<k>."
  }
}

variable "quota_project" {
  description = "Project that API quota is charged to: the seed, once it exists. Null on the first run."
  type        = string
  default     = null

  validation {
    condition     = var.quota_project == null || can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", coalesce(var.quota_project, "-")))
    error_message = "quota_project must be a project ID."
  }
}
