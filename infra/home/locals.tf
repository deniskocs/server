locals {
  ssh_private_key = var.ssh_private_key_base64 != null ? base64decode(var.ssh_private_key_base64) : null

  ssh_connection = {
    type        = "ssh"
    host        = var.mac_host
    user        = var.mac_user
    private_key = local.ssh_private_key
  }
}
