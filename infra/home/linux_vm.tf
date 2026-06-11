resource "null_resource" "linux_vm" {
  depends_on = [null_resource.utm]

  lifecycle {
    precondition {
      condition     = local.ssh_private_key != null
      error_message = "Provide ssh_private_key_base64."
    }
  }

  triggers = {
    linux_vm_name             = var.linux_vm_name
    linux_image_url           = var.linux_image_url
    linux_image_path          = var.linux_image_path
    static_ip                 = var.static_ip
    network_prefix            = tostring(var.network_prefix)
    network_gateway           = var.network_gateway
    dns_servers               = join(",", var.dns_servers)
    linux_vm_memory_mb        = tostring(var.linux_vm_memory_mb)
    linux_vm_cpu_cores        = tostring(var.linux_vm_cpu_cores)
    linux_vm_disk_gb          = tostring(var.linux_vm_disk_gb)
    linux_vm_network_mode     = var.linux_vm_network_mode
    linux_vm_bridge_interface = var.linux_vm_bridge_interface
    utm_documents_dir         = var.utm_documents_dir
    utm_run_as_user           = var.utm_run_as_user
  }

  provisioner "remote-exec" {
    inline = [templatefile("${path.module}/scripts/create-linux-vm.sh.tpl", {
      linux_vm_name             = var.linux_vm_name
      linux_image_url           = var.linux_image_url
      linux_image_path          = var.linux_image_path
      static_ip                 = var.static_ip
      network_prefix            = var.network_prefix
      network_gateway           = var.network_gateway
      dns_servers               = join(", ", var.dns_servers)
      linux_vm_memory_mb        = var.linux_vm_memory_mb
      linux_vm_cpu_cores        = var.linux_vm_cpu_cores
      linux_vm_disk_gb          = var.linux_vm_disk_gb
      linux_vm_network_mode     = var.linux_vm_network_mode
      linux_vm_bridge_interface = var.linux_vm_bridge_interface
      utm_documents_dir         = var.utm_documents_dir
      utm_run_as_user           = var.utm_run_as_user
    })]

    connection {
      type        = local.ssh_connection.type
      host        = local.ssh_connection.host
      user        = local.ssh_connection.user
      private_key = local.ssh_connection.private_key
    }
  }
}
