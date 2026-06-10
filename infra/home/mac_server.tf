resource "null_resource" "mac_server_dir" {
  lifecycle {
    precondition {
      condition     = local.ssh_private_key != null
      error_message = "Provide ssh_private_key_base64."
    }

    precondition {
      condition     = can(regex("^[a-zA-Z0-9._-]+$", var.dir_name))
      error_message = "dir_name must be a single directory name inside user home (no slashes or ..)."
    }
  }

  triggers = {
    dir_name = var.dir_name
  }

  provisioner "remote-exec" {
    inline = [
      "set -e",
      "TARGET=\"$HOME/${var.dir_name}\"",
      "if [ -d \"$TARGET\" ]; then",
      "  echo \"Directory already exists: $TARGET\"",
      "else",
      "  mkdir -p \"$TARGET\"",
      "  echo \"Created: $TARGET\"",
      "fi",
    ]

    connection {
      type        = local.ssh_connection.type
      host        = local.ssh_connection.host
      user        = local.ssh_connection.user
      private_key = local.ssh_connection.private_key
    }
  }
}
