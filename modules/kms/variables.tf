variable "project_id" {
  description = "Project that holds the key ring."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid project ID."
  }
}

variable "location" {
  description = "Key ring location, e.g. europe-north1. A key's location can never change."
  type        = string

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+[0-9]+)?$", var.location))
    error_message = "location must be a region such as europe-north1 or a multi-region such as europe."
  }
}

variable "key_ring" {
  description = "Key ring name. Key rings can't be deleted, so choose it once."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]{1,63}$", var.key_ring))
    error_message = "key_ring must be 1-63 letters, digits, '_' or '-'."
  }
}

variable "keys" {
  description = <<-EOT
    Keys to create, by name. Each key's whole IAM policy is managed: the listed members are the
    only ones with any role on it. Members are service accounts (including the Cloud Storage
    service agent) or groups; never users, principal sets or public principals.
  EOT
  type = map(object({
    rotation_period       = optional(string, "7776000s")
    encrypters_decrypters = optional(set(string), [])
    decrypters            = optional(set(string), [])
  }))

  validation {
    condition     = length(var.keys) > 0 && alltrue([for name in keys(var.keys) : can(regex("^[a-zA-Z0-9_-]{1,63}$", name))])
    error_message = "keys must name at least one key, using 1-63 letters, digits, '_' or '-'."
  }

  validation {
    condition = alltrue([
      for key in values(var.keys) :
      can(regex("^[0-9]+s$", key.rotation_period)) && try(tonumber(trimsuffix(key.rotation_period, "s")) >= 86400, false)
    ])
    error_message = "rotation_period must be whole seconds such as 7776000s, at least one day (86400s)."
  }

  validation {
    condition = alltrue(flatten([
      for key in values(var.keys) : [
        for member in setunion(key.encrypters_decrypters, key.decrypters) :
        can(regex("^(serviceAccount:[a-z0-9-]+@[a-z0-9-]+\\.iam\\.gserviceaccount\\.com|serviceAccount:service-[0-9]+@gs-project-accounts\\.iam\\.gserviceaccount\\.com|group:[a-z0-9._-]+@[a-z0-9.-]+\\.[a-z]+)$", member))
      ]
    ]))
    error_message = "members must be serviceAccount:<name>@<project>.iam.gserviceaccount.com, the Cloud Storage service agent, or group:<address>."
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
