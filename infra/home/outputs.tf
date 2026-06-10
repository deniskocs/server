output "mac_host" {
  description = "Целевой Mac host"
  value       = var.mac_host
}

output "utm_cask" {
  description = "Homebrew cask для UTM"
  value       = var.utm_cask
}

output "utm_app_path" {
  description = "Путь к UTM.app на Mac"
  value       = "/Applications/UTM.app"
}
