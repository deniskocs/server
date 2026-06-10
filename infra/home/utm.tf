resource "null_resource" "utm" {
  lifecycle {
    precondition {
      condition     = local.ssh_private_key != null
      error_message = "Provide ssh_private_key_base64."
    }
  }

  triggers = {
    utm_cask = var.utm_cask
  }

  provisioner "remote-exec" {
    script = "${path.module}/scripts/install-utm.sh"

    environment = {
      UTM_CASK = var.utm_cask
    }

    connection {
      type        = local.ssh_connection.type
      host        = local.ssh_connection.host
      user        = local.ssh_connection.user
      private_key = local.ssh_connection.private_key
    }
  }
}
