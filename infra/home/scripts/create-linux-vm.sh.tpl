#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

UTMCTL="/Applications/UTM.app/Contents/MacOS/utmctl"
VM_NAME="${linux_vm_name}"
IMAGE_URL="${linux_image_url}"
IMAGE_PATH="${linux_image_path}"
IMAGE_PATH="$${IMAGE_PATH/#\~/$HOME}"
STATIC_IP="${static_ip}"
GATEWAY="${network_gateway}"
MEMORY_MB="${linux_vm_memory_mb}"
CPU_CORES="${linux_vm_cpu_cores}"
DISK_GB="${linux_vm_disk_gb}"
NETWORK_MODE="${linux_vm_network_mode}"
BRIDGE_INTERFACE="${linux_vm_bridge_interface}"

if [ ! -x "$UTMCTL" ]; then
  echo "utmctl not found at $UTMCTL — install UTM first" >&2
  exit 1
fi

vm_exists() {
  osascript -e 'tell application "UTM" to get name of every virtual machine' \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
    | grep -qxF "$VM_NAME"
}

if vm_exists; then
  echo "UTM VM '$VM_NAME' already exists"
  exit 0
fi

mkdir -p "$(dirname "$IMAGE_PATH")"

if [ ! -f "$IMAGE_PATH" ]; then
  echo "Downloading Linux image from $IMAGE_URL ..."
  curl -fsSL "$IMAGE_URL" -o "$IMAGE_PATH.part"
  mv "$IMAGE_PATH.part" "$IMAGE_PATH"
  echo "Linux image saved to $IMAGE_PATH"
else
  echo "Using existing Linux image at $IMAGE_PATH"
fi

SEED_DIR="$(mktemp -d)"
trap 'rm -rf "$SEED_DIR"' EXIT
SEED_ISO="$SEED_DIR/cidata.iso"

cat > "$SEED_DIR/user-data" <<EOF
#cloud-config
hostname: $VM_NAME
manage_etc_hosts: true
ssh_pwauth: true
users:
  - default
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
package_update: true
package_upgrade: false
EOF

cat > "$SEED_DIR/network-config" <<EOF
version: 2
ethernets:
  eth0:
    dhcp4: false
    addresses:
      - ${static_ip}/${network_prefix}
EOF

cat >> "$SEED_DIR/network-config" <<EOF
    routes:
      - to: default
        via: ${network_gateway}
    nameservers:
      addresses: [${dns_servers}]
EOF

create_seed_iso() {
  if command -v genisoimage >/dev/null 2>&1; then
    genisoimage -output "$SEED_ISO" -V cidata -r -J \
      "$SEED_DIR/user-data" "$SEED_DIR/network-config"
    return 0
  fi

  if command -v mkisofs >/dev/null 2>&1; then
    mkisofs -output "$SEED_ISO" -V cidata -r -J \
      "$SEED_DIR/user-data" "$SEED_DIR/network-config"
    return 0
  fi

  hdiutil makehybrid -iso -joliet -default-volume-name cidata \
    -o "$SEED_ISO" "$SEED_DIR" >/dev/null
}

echo "Creating cloud-init seed ISO ..."
create_seed_iso

HEADLESS_CONFIG="displays:{}, serial ports:{}"

if [ "$NETWORK_MODE" = "bridged" ] && [ -n "$BRIDGE_INTERFACE" ]; then
  NETWORK_CONFIG="{{mode:bridged, host interface:\"$BRIDGE_INTERFACE\"}}"
else
  NETWORK_CONFIG="{{mode:$NETWORK_MODE}}"
fi

echo "Creating headless UTM VM '$VM_NAME' ..."
osascript <<APPLESCRIPT
tell application "UTM"
  set diskPath to POSIX file "$IMAGE_PATH"
  set seedPath to POSIX file "$SEED_ISO"
  set newVM to make new virtual machine with properties {backend:qemu, configuration:{name:"$VM_NAME", notes:"Managed by Terraform infra/home (headless)", architecture:"aarch64", memory:$MEMORY_MB, cpu cores:$CPU_CORES, drives:{{removable:true, source:seedPath}, {source:diskPath, guest size:$((DISK_GB * 1024))}}, network interfaces:{$NETWORK_CONFIG}, $HEADLESS_CONFIG}}
  update configuration of newVM with {$HEADLESS_CONFIG}
end tell
APPLESCRIPT

echo "Starting VM '$VM_NAME' ..."
"$UTMCTL" start "$VM_NAME"

echo "Linux VM '$VM_NAME' created (static: $STATIC_IP)"
