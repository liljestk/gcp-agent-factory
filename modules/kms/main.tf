resource "google_kms_key_ring" "this" {
  project  = var.project_id
  name     = var.key_ring
  location = var.location
}

# Nothing is granted on the key ring itself: access is per key. Keeping its policy empty and
# authoritative makes any key-ring grant, which every key would inherit, show up as drift.
data "google_iam_policy" "key_ring" {}

resource "google_kms_key_ring_iam_policy" "this" {
  key_ring_id = google_kms_key_ring.this.id
  policy_data = data.google_iam_policy.key_ring.policy_data
}

resource "google_kms_crypto_key" "this" {
  for_each = var.keys

  name            = each.key
  key_ring        = google_kms_key_ring.this.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = each.value.rotation_period
  labels          = var.labels

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  # Keys can't be deleted, and losing one makes everything encrypted with it unreadable.
  lifecycle {
    prevent_destroy = true
  }
}

# Each key's whole policy is managed: the listed members are the only ones with any role on it,
# and a key with no members has an empty policy.
data "google_iam_policy" "key" {
  for_each = var.keys

  dynamic "binding" {
    for_each = length(each.value.encrypters_decrypters) > 0 ? [each.value.encrypters_decrypters] : []
    content {
      role    = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
      members = sort(tolist(binding.value))
    }
  }

  dynamic "binding" {
    for_each = length(each.value.decrypters) > 0 ? [each.value.decrypters] : []
    content {
      role    = "roles/cloudkms.cryptoKeyDecrypter"
      members = sort(tolist(binding.value))
    }
  }
}

resource "google_kms_crypto_key_iam_policy" "this" {
  for_each = var.keys

  crypto_key_id = google_kms_crypto_key.this[each.key].id
  policy_data   = data.google_iam_policy.key[each.key].policy_data
}
