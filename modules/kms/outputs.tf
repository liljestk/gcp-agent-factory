output "key_ring_id" {
  description = "Key ring ID."
  value       = google_kms_key_ring.this.id
}

output "key_ids" {
  description = "Crypto key IDs by key name. Available only once each key's IAM policy is set, so a bucket using a key as CMEK doesn't race its grant."
  value       = { for name, key in google_kms_crypto_key.this : name => key.id }
  depends_on  = [google_kms_crypto_key_iam_policy.this, google_kms_key_ring_iam_policy.this]
}
