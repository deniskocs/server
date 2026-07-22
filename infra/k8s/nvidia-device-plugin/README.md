# NVIDIA device plugin (k3s)

Регистрирует `nvidia.com/gpu` на нодах с меткой **`rtx-titan=true`** или **`rtx-6000-pro=true`**. Argo Application **`server`**.

## Одноразово на GPU-ноде

Если GPU-поды не стартуют или `RuntimeClass nvidia` не работает — перезапуск агента, чтобы k3s подхватил nvidia runtime в containerd:

```bash
sudo systemctl restart k3s-agent
sudo grep nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
```

Пакеты на ноде: `nvidia-container-toolkit`, драйвер, `nvidia-smi`.

## Проверка

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
kubectl get pods -n kube-system -l app=nvidia-device-plugin
```

GPU-поды должны иметь `runtimeClassName: nvidia` и `nodeSelector` на нужную метку (`rtx-titan` / `rtx-6000-pro`).
