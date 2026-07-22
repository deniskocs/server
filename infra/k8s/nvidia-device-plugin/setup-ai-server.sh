#!/bin/bash
# Одноразовая настройка k3s-agent на GPU-ноде (rtx-titan / 10.0.0.3). Нужен sudo.
set -e

CONFIG=/etc/rancher/k3s/config.yaml
sudo mkdir -p /etc/rancher/k3s

if [ -f "$CONFIG" ] && grep -q '^default-runtime:' "$CONFIG"; then
  echo "default-runtime already set in $CONFIG"
else
  echo 'default-runtime: nvidia' | sudo tee -a "$CONFIG"
fi

echo "Restarting k3s-agent..."
sudo systemctl restart k3s-agent
sleep 5
sudo grep -i nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -5 || true
echo "Done. Check: kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu"
