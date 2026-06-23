# Home cluster — bootstrap Argo CD

Terraform-стек для **homelab k3s**: установка Argo CD до GitOps.

Управляет:

- namespace `argocd`;
- Helm release `argo-cd` ([argo-helm](https://github.com/argoproj/argo-helm), values — `values/argocd.yaml`).

**Не управляет** Application в GitOps — каждый репозиторий регистрирует свой Application сам (`infra/k8s/argocd/` для `server`, `deploy/argocd/` в tzone и т.д.).

Пара с **`infra/home-lab/`** (AWS DNS `chilik.net`). GitOps-манифесты — **`infra/k8s/server/`**.

## Где запускать

**На master node**, где `kubectl` уже имеет доступ к кластеру.

## Apply

```bash
cd server/infra/home-cluster
terraform init
terraform plan
terraform apply
```

После первой установки — одноразово зарегистрировать Application `server`: [`../k8s/argocd/README.md`](../k8s/argocd/README.md).

## Миграция state из `infra/k8s/platform`

Backend key: `k8s/platform/terraform.tfstate` → **`home-cluster/terraform.tfstate`**.

```bash
# 1. Скопировать state в S3 (AWS не трогает ресурсы в кластере)
aws s3 cp s3://deniskocs-terraform-states/k8s/platform/terraform.tfstate \
          s3://deniskocs-terraform-states/home-cluster/terraform.tfstate

# 2. В новом каталоге
cd server/infra/home-cluster
terraform init
terraform plan   # ожидается: No changes
```

Старый ключ в S3 можно удалить после успешного `plan`.

## GitOps: кто что регистрирует

| Application | Регистрация |
|-------------|-------------|
| **server** | `infra/k8s/argocd/application.yaml` + kubectl apply |
| **tzone** | `tzone/deploy/argocd/application.yaml` |
| **learn-english** | `learn-english-backend/infra/argocd/application.yaml` |

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `kubeconfig_path` | `~/.kube/config` | Путь к kubeconfig |
| `argocd_chart_version` | `7.8.0` | Версия Helm chart argo-cd |
| `argocd_namespace` | `argocd` | Namespace Argo CD |
