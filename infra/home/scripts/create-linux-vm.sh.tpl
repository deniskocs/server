#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

UTM_APP="/Applications/UTM.app"
UTMCTL="$${UTM_APP}/Contents/MacOS/utmctl"
UTM_DATA="$${HOME}/Library/Containers/com.utmapp.UTM/Data/Documents"

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

utm_ready() {
  "$UTMCTL" list >/dev/null 2>&1
}

vm_registered() {
  "$UTMCTL" list 2>/dev/null | awk -v name="$VM_NAME" '$1 == name { found=1 } END { exit !found }'
}

ensure_utm_running() {
  if utm_ready; then
    return 0
  fi

  echo "Launching UTM via utmctl/UTM.app ..."
  open "$UTM_APP"

  for _ in $(seq 1 30); do
    if utm_ready; then
      return 0
    fi
    sleep 1
  done

  echo "UTM did not become ready for utmctl" >&2
  exit 1
}

ensure_vm_registered() {
  ensure_utm_running

  if vm_registered; then
    return 0
  fi

  echo "Restarting UTM so it picks up the new VM ..."
  killall UTM 2>/dev/null || true
  sleep 2
  open "$UTM_APP"

  for _ in $(seq 1 30); do
    if utm_ready && vm_registered; then
      return 0
    fi
    sleep 1
  done

  echo "UTM did not register VM '$VM_NAME'" >&2
  exit 1
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
  [ -d "$VM_DIR" ] && return 0
  "$UTMCTL" list 2>/dev/null | awk -v name="$VM_NAME" '$1 == name { found=1 } END { exit !found }'
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

mkdir -p "$${VM_DIR}/Data"

SEED_FILE="$${VM_DIR}/Data/$${SEED_UUID}.iso"
DISK_FILE="$${VM_DIR}/Data/$${DISK_UUID}.qcow2"

cp "$SEED_ISO" "$SEED_FILE"

QEMU_IMG="$(find_qemu_img || true)"
if [ -n "$QEMU_IMG" ]; then
  echo "Preparing VM disk from cloud image with $QEMU_IMG ..."
  "$QEMU_IMG" convert -O qcow2 "$IMAGE_PATH" "$DISK_FILE"
  "$QEMU_IMG" resize "$DISK_FILE" "$${DISK_GB}G"
else
  echo "qemu-img not found, linking cloud image as VM disk ..."
  ln -sf "$IMAGE_PATH" "$DISK_FILE"
fi

BRIDGE_INTERFACE_XML=""
if [ -n "$BRIDGE_INTERFACE" ]; then
  BRIDGE_INTERFACE_XML="        <key>BridgeInterface</key>
        <string>$${BRIDGE_INTERFACE}</string>"
fi

echo "Writing UTM config.plist for headless VM '$VM_NAME' ..."
cat > "$CONFIG_PLIST" <<EOF
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

ensure_vm_registered

echo "Starting VM '$VM_NAME' with utmctl ..."
"$UTMCTL" start "$VM_NAME"

echo "Linux VM '$VM_NAME' created (static: $STATIC_IP)"
