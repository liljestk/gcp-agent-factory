output "labels" {
  description = "Standard label map to pass to every labelable resource."
  value       = tomap(local.labels)
}
