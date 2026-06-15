# K8s platform — Argo CD

Terraform-стек для ресурсов **внутри уже существующего** Kubernetes-кластера.

Управляет:

- namespace `argocd`;
- Helm release `argo-cd` (официальный chart [argo-helm](https://github.com/argoproj/argo-helm));
- Helm release `argocd-apps` — корневой **app-of-apps**, который создаёт дочерние Argo CD `Application` из каталога `applications/`.

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

## App-of-apps (автосоздание приложений)

Приложения в кластере регистрируются по схеме **app-of-apps**:

- `argocd-apps.tf` + `values/argocd-apps.yaml` — корневой `Application` (`platform-root`), который следит за каталогом `applications/` в репозитории `server`;
- `applications/*.yaml` — дочерние `Application` только верхнего уровня:
  - **`tzone`** — манифесты из репозитория `tzone` (`deploy/k8s`);
  - **`server`** — всё платформенное из этого репозитория (`infra/k8s/server`, Kustomize).

После `terraform apply` корневой app создаётся автоматически и подтягивает всё из `applications/`. **Добавить новое приложение** = положить новый `Application`-манифест в `applications/`, закоммитить и запушить — Argo CD создаст его сам, без `kubectl apply` и без `terraform apply`.

> Требование: Argo CD должен иметь доступ по SSH к репозиторию `git@github.com:deniskocs/server.git` (так же, как к `tzone`). Проверить: `argocd repo list` или Settings → Repositories в UI. При необходимости добавить репозиторий/ключ.

## Remote state (опционально)

После bootstrap S3 (`server/infra/terraform`) раскомментируйте `backend "s3"` в `versions.tf` и подставьте имя bucket из `terraform output state_bucket_name`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `kubeconfig_path` | `~/.kube/config` | Путь к kubeconfig |
| `argocd_chart_version` | `7.8.0` | Версия Helm chart argo-cd |
| `argocd_apps_chart_version` | `2.0.5` | Версия Helm chart argocd-apps (app-of-apps) |
| `argocd_namespace` | `argocd` | Namespace Argo CD |
