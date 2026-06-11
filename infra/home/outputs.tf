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

output "linux_vm_name" {
  description = "Имя Linux VM в UTM"
  value       = var.linux_vm_name
}

output "linux_vm_static_ip" {
  description = "Статический IP Linux VM"
  value       = var.static_ip
}

output "linux_image_url" {
  description = "URL cloud-образа Linux"
  value       = var.linux_image_url
}
