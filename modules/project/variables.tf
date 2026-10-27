variable "project_id" {
  description = "Project ID: 6-30 characters, lowercase letters, digits and hyphens, starting with a letter."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be 6-30 characters of lowercase letters, digits and hyphens, start with a letter and not end with a hyphen."
  }
}

variable "name" {
  description = "Display name of the project."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9 '!-]{4,30}$", var.name))
    error_message = "name must be 4-30 characters of letters, digits, spaces, hyphens, single quotes or exclamation marks."
  }
}

variable "folder_id" {
  description = "Parent folder, as \"folders/<number>\" or the bare number."
  type        = string

  validation {
    condition     = can(regex("^(folders/)?[0-9]+$", var.folder_id))
    error_message = "folder_id must be \"folders/<number>\" or a number."
  }
}

variable "billing_account" {
  description = "Billing account ID to link, e.g. 012345-6789AB-CDEF01."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}$", var.billing_account))
    error_message = "billing_account must look like 012345-6789AB-CDEF01."
  }
}

variable "delete_default_network" {
  description = "Delete the default network. This turns the Compute Engine API on; leave it false for projects that never enable compute."
  type        = bool
  default     = false
}

variable "services" {
  description = "APIs to enable and manage, e.g. cloudkms.googleapis.com. APIs Google enables by default are left alone."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for service in var.services : can(regex("^[a-z][a-z0-9-]*\\.googleapis\\.com$", service))])
    error_message = "services must be API names ending in .googleapis.com."
  }
}

variable "labels" {
  description = "Standard labels from modules/labels."
  type        = map(string)

  validation {
    condition     = contains(keys(var.labels), "managed-by") && contains(keys(var.labels), "repo")
    error_message = "labels must come from modules/labels (they need at least managed-by and repo)."
  }
}

variable "deletion_policy" {
  description = "What `tofu destroy` does with the project: PREVENT (refuse), ABANDON (leave it) or DELETE."
  type        = string
  default     = "PREVENT"

  validation {
    condition     = contains(["PREVENT", "ABANDON", "DELETE"], var.deletion_policy)
    error_message = "deletion_policy must be PREVENT, ABANDON or DELETE."
  }
}

variable "lien_reason" {
  description = "When set, a lien blocks deleting the project and records this reason. Null means no lien."
  type        = string
  default     = null

  validation {
    condition     = try(length(var.lien_reason) > 0, true)
    error_message = "lien_reason must be null or a non-empty string."
  }
}
