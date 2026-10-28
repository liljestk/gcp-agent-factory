output "pool_name" {
  description = "Full resource name of the workload identity pool."
  value       = google_iam_workload_identity_pool.github.name
}

output "provider_name" {
  description = "Full resource name of the provider, for google-github-actions/auth's workload_identity_provider."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "principal_sets" {
  description = "The principal set each service account trusts, by account name."
  value       = { for name, binding in google_service_account_iam_binding.workload_identity_user : name => one(binding.members) }
}

output "gates" {
  description = "The trust condition and the plan and deploy gates as deployed, for the live checks."
  value       = local.gates
}
