locals {
  standard = {
    env           = var.env
    platform      = var.platform
    component     = var.component
    owner         = var.owner
    "cost-center" = var.cost_center
    "managed-by"  = "opentofu"
    repo          = var.repo
  }

  optional = {
    for key, value in {
      agent          = var.agent
      app            = var.app
      "data-product" = var.data_product
    } : key => value if value != null
  }

  # Standard keys win; validation already rejects extra keys that collide with them.
  labels = merge(var.extra, local.optional, local.standard)
}
