output "mac_host" {
  description = "Целевой Mac host"
  value       = var.mac_host
}

output "dir_name" {
  description = "Имя каталога в home пользователя"
  value       = var.dir_name
}

output "home_dir_path" {
  description = "Путь к каталогу относительно home (~/<dir_name>)"
  value       = local.home_dir_path
}
