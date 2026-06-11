variable "mac_host" {
  description = "Хост Mac Studio (MAC_HOST в GitHub Secrets)"
  type        = string
}

variable "mac_user" {
  description = "SSH-пользователь на Mac (MAC_USER в GitHub Secrets)"
  type        = string
}

variable "ssh_private_key_base64" {
  description = "Приватный SSH-ключ в base64 (как SSH_PRIVATE_KEY_DEPLOY_TO_MAC_SERVER_BASE64 в CI)"
  type        = string
  sensitive   = true
  default     = null
}

variable "utm_cask" {
  description = "Имя Homebrew cask для UTM"
  type        = string
  default     = "utm"
}

variable "linux_vm_name" {
  description = "Имя виртуальной машины Linux в UTM"
  type        = string
  default     = "linux"
}

variable "linux_image_url" {
  description = "URL cloud-образа Linux (aarch64) для скачивания на Mac"
  type        = string
  default     = "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-arm64.img"
}

variable "linux_image_path" {
  description = "Путь на Mac, куда сохранять скачанный образ Linux"
  type        = string
  default     = "~/Library/Application Support/utm/linux/ubuntu-24.04-server-cloudimg-arm64.img"
}

variable "static_ip" {
  description = "Статический IP-адрес Linux VM"
  type        = string
  default     = "10.0.0.6"
}

variable "network_prefix" {
  description = "Длина префикса подсети 10.0.0.0/24 для static IP (CIDR)"
  type        = number
  default     = 24
}

variable "network_gateway" {
  description = "Шлюз по умолчанию для Linux VM"
  type        = string
  default     = "10.0.0.1"
}

variable "dns_servers" {
  description = "DNS-серверы для cloud-init network-config"
  type        = list(string)
  default     = ["8.8.8.8", "1.1.1.1"]
}

variable "linux_vm_memory_mb" {
  description = "RAM Linux VM в MiB"
  type        = number
  default     = 4096
}

variable "linux_vm_cpu_cores" {
  description = "Число CPU Linux VM"
  type        = number
  default     = 4
}

variable "linux_vm_disk_gb" {
  description = "Размер диска Linux VM в GiB (если образ меньше — расширяется)"
  type        = number
  default     = 32
}

variable "linux_vm_network_mode" {
  description = "Режим сети UTM: shared, bridged, emulated или host"
  type        = string
  default     = "bridged"

  validation {
    condition     = contains(["shared", "bridged", "emulated", "host"], var.linux_vm_network_mode)
    error_message = "linux_vm_network_mode must be one of: shared, bridged, emulated, host."
  }
}

variable "linux_vm_bridge_interface" {
  description = "Интерфейс хоста для bridged-режима (например en0); пусто — интерфейс по умолчанию UTM"
  type        = string
  default     = ""
}
