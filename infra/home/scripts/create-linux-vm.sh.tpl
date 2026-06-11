#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

UTM_APP="/Applications/UTM.app"
UTMCTL="$${UTM_APP}/Contents/MacOS/utmctl"
UTM_DATA="${utm_documents_dir}"
UTM_RUN_AS="${utm_run_as_user}"

if [ -z "$UTM_DATA" ]; then
  UTM_DATA="$${HOME}/Library/Containers/com.utmapp.UTM/Data/Documents"
fi

run_utm_user() {
  if [ -n "$UTM_RUN_AS" ] && [ "$$(id -un)" != "$UTM_RUN_AS" ]; then
    sudo -u "$UTM_RUN_AS" "$@"
  else
    "$@"
  fi
}

VM_NAME="${linux_vm_name}"
IMAGE_URL="${linux_image_url}"
IMAGE_PATH="${linux_image_path}"
IMAGE_PATH="$${IMAGE_PATH/#\~/$HOME}"
STATIC_IP="${static_ip}"
MEMORY_MB="${linux_vm_memory_mb}"
CPU_CORES="${linux_vm_cpu_cores}"
DISK_GB="${linux_vm_disk_gb}"
NETWORK_MODE="${linux_vm_network_mode}"
BRIDGE_INTERFACE="${linux_vm_bridge_interface}"

VM_DIR="$${UTM_DATA}/${linux_vm_name}.utm"
CONFIG_PLIST="$${VM_DIR}/config.plist"

if [ ! -x "$UTMCTL" ]; then
  echo "utmctl not found at $UTMCTL — install UTM first" >&2
  exit 1
fi

if [ ! -d "$UTM_APP" ]; then
  echo "UTM.app not found at $UTM_APP" >&2
  exit 1
fi

find_qemu_img() {
  local candidate
  for candidate in \
    "$(command -v qemu-img 2>/dev/null || true)" \
    "$${UTM_APP}/Contents/MacOS/qemu-img" \
    "/opt/homebrew/bin/qemu-img" \
    "/usr/local/bin/qemu-img"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

start_vm() {
  echo "Starting VM '$VM_NAME' with utmctl (user: $${UTM_RUN_AS:-$$(id -un)}) ..."
  run_utm_user open "$UTM_APP" >/dev/null 2>&1 || true
  sleep 5

  if run_utm_user "$UTMCTL" start "$VM_NAME"; then
    echo "VM '$VM_NAME' started"
    return 0
  fi

  echo "WARNING: utmctl start failed."
  echo "UTM/utmctl require an interactive GUI session for the same macOS user as UTM.app."
  echo "Log in as $${UTM_RUN_AS:-the UTM owner} on the Mac console and run:"
  echo "  $UTMCTL start $VM_NAME"
  return 0
}

utm_network_mode() {
  case "$1" in
    bridged) echo "Bridged" ;;
    shared) echo "Shared" ;;
    emulated) echo "Emulated" ;;
    host) echo "Host" ;;
    *) echo "Shared" ;;
  esac
}

vm_exists() {
  [ -d "$VM_DIR" ] && [ -f "$CONFIG_PLIST" ]
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
SEED_ISO="$SEED_DIR/cidata.iso"
trap 'rm -rf "$SEED_DIR"' EXIT

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

SEED_UUID="$(uuidgen)"
DISK_UUID="$(uuidgen)"
VM_UUID="$(uuidgen)"
MAC_ADDRESS="$(printf '52:54:00:%02x:%02x:%02x' $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)))"
NETWORK_MODE_PLIST="$(utm_network_mode "$NETWORK_MODE")"

run_utm_user mkdir -p "$${VM_DIR}/Data"

SEED_FILE="$${VM_DIR}/Data/$${SEED_UUID}.iso"
DISK_FILE="$${VM_DIR}/Data/$${DISK_UUID}.qcow2"

run_utm_user cp "$SEED_ISO" "$SEED_FILE"

QEMU_IMG="$(find_qemu_img || true)"
if [ -n "$QEMU_IMG" ]; then
  echo "Preparing VM disk from cloud image with $QEMU_IMG ..."
  run_utm_user "$QEMU_IMG" convert -O qcow2 "$IMAGE_PATH" "$DISK_FILE"
  run_utm_user "$QEMU_IMG" resize "$DISK_FILE" "$${DISK_GB}G"
else
  echo "qemu-img not found, linking cloud image as VM disk ..."
  run_utm_user ln -sf "$IMAGE_PATH" "$DISK_FILE"
fi

BRIDGE_INTERFACE_XML=""
if [ -n "$BRIDGE_INTERFACE" ]; then
  BRIDGE_INTERFACE_XML="        <key>BridgeInterface</key>
        <string>$${BRIDGE_INTERFACE}</string>"
fi

echo "Writing UTM config.plist for headless VM '$VM_NAME' ..."
run_utm_user tee "$CONFIG_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Backend</key>
    <string>QEMU</string>
    <key>ConfigurationVersion</key>
    <integer>4</integer>
    <key>System</key>
    <dict>
        <key>Architecture</key>
        <string>aarch64</string>
        <key>CPU</key>
        <string>default</string>
        <key>CPUCount</key>
        <integer>$${CPU_CORES}</integer>
        <key>MemorySize</key>
        <integer>$${MEMORY_MB}</integer>
        <key>Target</key>
        <string>virt</string>
    </dict>
    <key>QEMU</key>
    <dict>
        <key>Hypervisor</key>
        <true/>
        <key>UEFIBoot</key>
        <true/>
    </dict>
    <key>Input</key>
    <dict>
        <key>UsbSharing</key>
        <false/>
    </dict>
    <key>Drive</key>
    <array>
        <dict>
            <key>Identifier</key>
            <string>$${SEED_UUID}</string>
            <key>ImageName</key>
            <string>$${SEED_UUID}.iso</string>
            <key>ImageType</key>
            <string>CD</string>
            <key>Interface</key>
            <string>USB</string>
            <key>InterfaceVersion</key>
            <integer>1</integer>
            <key>ReadOnly</key>
            <true/>
        </dict>
        <dict>
            <key>Identifier</key>
            <string>$${DISK_UUID}</string>
            <key>ImageName</key>
            <string>$${DISK_UUID}.qcow2</string>
            <key>ImageType</key>
            <string>Disk</string>
            <key>Interface</key>
            <string>VirtIO</string>
            <key>InterfaceVersion</key>
            <integer>1</integer>
            <key>ReadOnly</key>
            <false/>
        </dict>
    </array>
    <key>Network</key>
    <array>
        <dict>
            <key>Hardware</key>
            <string>virtio-net-pci</string>
            <key>Mode</key>
            <string>$${NETWORK_MODE_PLIST}</string>
            <key>IsolateFromHost</key>
            <false/>
            <key>MacAddress</key>
            <string>$${MAC_ADDRESS}</string>
$${BRIDGE_INTERFACE_XML}
        </dict>
    </array>
    <key>Information</key>
    <dict>
        <key>Name</key>
        <string>$${VM_NAME}</string>
        <key>UUID</key>
        <string>$${VM_UUID}</string>
        <key>Notes</key>
        <string>Managed by Terraform infra/home (headless)</string>
        <key>Icon</key>
        <string>linux</string>
        <key>IconCustom</key>
        <false/>
    </dict>
</dict>
</plist>
EOF

plutil -lint "$CONFIG_PLIST"

echo "UTM VM bundle: $VM_DIR"
start_vm

echo "Linux VM '$VM_NAME' created (static: $STATIC_IP)"
