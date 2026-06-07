# K8s platform — Argo CD

Terraform-стек для ресурсов **внутри уже существующего** Kubernetes-кластера.

Управляет:

- namespace `argocd`;
- Helm release `argo-cd` (официальный chart [argo-helm](https://github.com/argoproj/argo-helm)).

Отдельно от AWS-стека (`tzone/infra/terraform`) и bootstrap state bucket (`server/infra/terraform`).

## Где запускать

**На master node**, где `kubectl` уже имеет доступ к кластеру.

## Проверка перед apply

```bash
kubectl cluster-info
kubectl get nodes
```

## Apply

```bash
cd server/infra/k8s/platform
terraform init
terraform plan
terraform apply
```

## Проверка Argo CD

```bash
kubectl get pods -n argocd
kubectl get svc -n argocd
```

Пароль admin (после первой установки):

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

Доступ к UI локально:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Открыть https://localhost:8080 (логин `admin`, пароль из команды выше).

## Remote state (опционально)

После bootstrap S3 (`server/infra/terraform`) раскомментируйте `backend "s3"` в `versions.tf` и подставьте имя bucket из `terraform output state_bucket_name`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `kubeconfig_path` | `~/.kube/config` | Путь к kubeconfig |
| `argocd_chart_version` | `7.8.0` | Версия Helm chart |
| `argocd_namespace` | `argocd` | Namespace Argo CD |
