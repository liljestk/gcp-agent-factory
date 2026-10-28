output "project_id" {
  description = "Project ID. Available only once the listed APIs are on, so callers don't race them."
  value       = google_project.this.project_id
  depends_on  = [google_project_service.this]
}

output "number" {
  description = "Project number. Available only once the listed APIs are on."
  value       = google_project.this.number
  depends_on  = [google_project_service.this]
}

output "services" {
  description = "APIs this module enables and manages, sorted."
  value       = sort([for service in google_project_service.this : service.service])
}

output "folder_id" {
  description = "Parent folder, as the provider records it."
  value       = google_project.this.folder_id
}

output "lien" {
  description = "Name of the lien that blocks deleting the project, or null without one."
  value       = one(google_resource_manager_lien.this[*].name)
}
