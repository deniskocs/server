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

variable "dir_name" {
  description = "Имя каталога в home SSH-пользователя ($HOME/dir_name)"
  type        = string
  default     = "test_terraform"
}
