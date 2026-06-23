# K8s platform — Argo CD

Terraform-стек для ресурсов **внутри уже существующего** Kubernetes-кластера.

Управляет:

- namespace `argocd`;
- Helm release `argo-cd` (официальный chart [argo-helm](https://github.com/argoproj/argo-helm), values — `values/argocd.yaml`).

**Не управляет** списком Application в GitOps: каждый репозиторий регистрирует свой Application сам (`infra/k8s/argocd/` для `server`, `deploy/argocd/` в tzone и т.д.).

Отдельно от AWS-стека (`tzone/infra/terraform`) и bootstrap state bucket (`server/infra/bootstrap-s3-state`).

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

После первой установки Argo CD — одноразово зарегистрировать Application `server`: см. [`../argocd/README.md`](../argocd/README.md).

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

## GitOps: кто что регистрирует

| Application | Регистрация |
|-------------|-------------|
| **server** (platform k8s) | `infra/k8s/argocd/application.yaml` + kubectl apply |
| **tzone** | `tzone/deploy/argocd/application.yaml` |
| **learn-english** | `learn-english-backend/infra/argocd/application.yaml` |

> Argo CD должен иметь SSH-доступ к репозиториям, которые он синкает. Проверка: `argocd repo list`.

## Remote state (опционально)

После bootstrap S3 (`server/infra/bootstrap-s3-state`) раскомментируйте `backend "s3"` в `versions.tf` и подставьте имя bucket из `terraform output state_bucket_name`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `kubeconfig_path` | `~/.kube/config` | Путь к kubeconfig |
| `argocd_chart_version` | `7.8.0` | Версия Helm chart argo-cd |
| `argocd_namespace` | `argocd` | Namespace Argo CD |
