# Inputs for the github stack and every CI stack. None of these is secret: IDs identify, they
# don't authorize (ADR-0017).

output "org_id" {
  description = "Numeric organization ID."
  value       = var.org_id
}

output "customer_id" {
  description = "Directory customer ID, for the domain restriction (spec 003)."
  value       = var.customer_id
}

output "identity_domain" {
  description = "Domain of the platform's groups."
  value       = var.identity_domain
}

output "region" {
  description = "Region of the state bucket and keys."
  value       = var.region
}

output "folders" {
  description = "Top-level folders by name, as folders/<number>."
  value       = { for name, folder in google_folder.this : name => folder.name }
}

output "seed_project_id" {
  description = "Seed project ID; CI charges API quota to it."
  value       = module.seed.project_id
}

output "seed_project_number" {
  description = "Seed project number."
  value       = module.seed.number
}

output "state_bucket" {
  description = "Name of the state bucket."
  value       = google_storage_bucket.state.name
}

output "state_keys" {
  description = "State key IDs by scope (trust-root, shared, dev, prod), plus github for the github stack's owner-only state."
  value       = { for name, id in module.kms.key_ids : trimprefix(name, "state-") => id if startswith(name, "state-") }
}

output "workload_identity_provider" {
  description = "Full name of the GitHub provider, for google-github-actions/auth."
  value       = module.wif.provider_name
}

output "ci_service_accounts" {
  description = "CI service account emails by name."
  value       = local.ci_email
}

output "wif_gates" {
  description = "The trust condition and gates as deployed, for the live identity checks."
  value       = module.wif.gates
}
