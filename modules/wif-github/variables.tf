variable "project_id" {
  description = "Project that holds the workload identity pool (the seed project)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid project ID."
  }
}

variable "pool_id" {
  description = "Workload identity pool ID."
  type        = string
  default     = "github"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.pool_id)) && !startswith(var.pool_id, "gcp-")
    error_message = "pool_id must be 4-32 lowercase letters, digits or hyphens, starting with a letter and not with the reserved gcp- prefix."
  }
}

variable "provider_id" {
  description = "Workload identity pool provider ID."
  type        = string
  default     = "github-actions"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.provider_id)) && !startswith(var.provider_id, "gcp-")
    error_message = "provider_id must be 4-32 lowercase letters, digits or hyphens, starting with a letter and not with the reserved gcp- prefix."
  }
}

variable "repository" {
  description = "GitHub repository as owner/name. Used only to pin the apply workflow; trust is pinned by IDs."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$", var.repository))
    error_message = "repository must look like owner/name."
  }
}

variable "repository_id" {
  description = "Immutable numeric ID of the repository; the only repository whose tokens are accepted."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.repository_id))
    error_message = "repository_id must be the numeric repository ID."
  }
}

variable "repository_owner_id" {
  description = "Immutable numeric ID of the repository owner."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.repository_owner_id))
    error_message = "repository_owner_id must be the numeric owner ID."
  }
}

variable "owner_actor_id" {
  description = "Numeric user ID whose pull requests and dispatches may plan. Defaults to the repository owner."
  type        = string
  default     = null

  validation {
    condition     = var.owner_actor_id == null || can(regex("^[0-9]+$", coalesce(var.owner_actor_id, "0")))
    error_message = "owner_actor_id must be a numeric user ID."
  }
}

variable "apply_workflow" {
  description = "Path of the only workflow that may use the apply identities, on main."
  type        = string
  default     = ".github/workflows/tofu.yml"

  validation {
    condition     = can(regex("^\\.github/workflows/[A-Za-z0-9._-]+\\.ya?ml$", var.apply_workflow))
    error_message = "apply_workflow must be a file under .github/workflows/."
  }
}

variable "service_accounts" {
  description = <<-EOT
    CI service accounts by name. `gate = "plan"` lets the plan gate's allowed runs use the
    account; `gate = "deploy"` with `environment` lets only a push run of tofu.yml on main, in
    that GitHub environment, use it. Each account's Workload Identity User binding is
    authoritative.
  EOT
  type = map(object({
    email       = string
    gate        = string
    environment = optional(string)
  }))

  validation {
    condition     = alltrue([for account in values(var.service_accounts) : can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\\.iam\\.gserviceaccount\\.com$", account.email))])
    error_message = "email must be a user-managed service account email."
  }

  validation {
    condition = alltrue([
      for account in values(var.service_accounts) :
      (account.gate == "plan" && account.environment == null) ||
      (account.gate == "deploy" && can(regex("^[a-z][a-z0-9-]*$", coalesce(account.environment, "-"))) && account.environment != "none")
    ])
    error_message = "gate must be \"plan\" (no environment) or \"deploy\" with a lowercase environment name other than \"none\", the value every refused token maps to."
  }
}
