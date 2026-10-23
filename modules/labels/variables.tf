variable "env" {
  description = "Environment the resource belongs to."
  type        = string

  validation {
    condition     = contains(["shared", "dev", "prod"], var.env)
    error_message = "env must be one of: shared, dev, prod."
  }
}

variable "platform" {
  description = "Owning platform."
  type        = string

  validation {
    condition     = contains(["landing-zone", "agents", "data", "ops", "apps"], var.platform)
    error_message = "platform must be one of: landing-zone, agents, data, ops, apps."
  }
}

variable "component" {
  description = "Component within the platform, e.g. orchestrator or budget-enforcer."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{0,62}$", var.component))
    error_message = "component must start with a lowercase letter and contain only lowercase letters, digits, '_' or '-' (max 63)."
  }
}

variable "owner" {
  description = "Owning team or group slug."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{0,62}$", var.owner))
    error_message = "owner must start with a lowercase letter and contain only lowercase letters, digits, '_' or '-' (max 63)."
  }
}

variable "cost_center" {
  description = "Cost center for FinOps reporting."
  type        = string
  default     = "demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{0,62}$", var.cost_center))
    error_message = "cost_center must start with a lowercase letter and contain only lowercase letters, digits, '_' or '-' (max 63)."
  }
}

variable "repo" {
  description = "Repository that manages the resource."
  type        = string
  default     = "gcp-agent-factory"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{0,62}$", var.repo))
    error_message = "repo must be a valid GCP label value starting with a lowercase letter (max 63)."
  }
}

variable "agent" {
  description = "Agent name, for agent-owned resources."
  type        = string
  default     = null

  validation {
    condition     = var.agent == null || can(regex("^[a-z][a-z0-9-]{0,62}$", var.agent))
    error_message = "agent must be a lowercase kebab-case name (max 63)."
  }
}

variable "app" {
  description = "App name, for resources of apps landed through the landing zone."
  type        = string
  default     = null

  validation {
    condition     = var.app == null || can(regex("^[a-z][a-z0-9-]{0,62}$", var.app))
    error_message = "app must be a lowercase kebab-case name (max 63)."
  }
}

variable "data_product" {
  description = "Data product name, for data platform resources."
  type        = string
  default     = null

  validation {
    condition     = var.data_product == null || can(regex("^[a-z][a-z0-9_-]{0,62}$", var.data_product))
    error_message = "data_product must be a valid GCP label value starting with a lowercase letter (max 63)."
  }
}

variable "extra" {
  description = "Additional labels. Keys and values must follow GCP label rules and may not override standard keys."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for key, value in var.extra :
      can(regex("^[a-z][a-z0-9_-]{0,62}$", key)) && can(regex("^[a-z0-9_-]{0,63}$", value))
    ])
    error_message = "extra label keys must start with a lowercase letter; keys and values may only contain lowercase letters, digits, '_' or '-' (max 63)."
  }

  validation {
    condition = length(setintersection(keys(var.extra), [
      "env", "platform", "component", "owner", "cost-center", "managed-by", "repo", "agent", "app", "data-product",
    ])) == 0
    error_message = "extra labels may not override standard label keys."
  }
}
