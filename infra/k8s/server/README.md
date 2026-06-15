# Серверный стек в Kubernetes

Сюда складываются манифесты, которые Argo CD синхронизирует **одним** приложением `server` (см. `infra/k8s/platform/applications/server.yaml`).

- Верхний уровень app-of-apps: только короткие `Application` в `infra/k8s/platform/applications/` (`tzone`, `server`).
- Всё содержимое деплоя из этого репозитория — под `infra/k8s/server/` (подкаталоги + записи в `kustomization.yaml`).

Порядок применения при необходимости задаётся аннотациями sync-wave Argo CD (`argocd.argoproj.io/sync-wave`).

## cert-manager (Helm)

Ставится через [helmCharts](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/helmcharts/) в `kustomization.yaml`, значения — `cert-manager-values.yaml` (`crds.enabled: true`).

После установки создаётся `ClusterIssuer` **`selfsigned`** — им можно выпускать внутренние сертификаты (например для `bitwarden-sdk-server`), без публичного DNS.

Локально: `kubectl kustomize infra/k8s/server --enable-helm` нужен **Helm** в `PATH`; в Argo CD Helm уже есть в `repo-server`.

### Let's Encrypt — не сразу

ACME (Let’s Encrypt) имеет смысл подключать, когда:

- есть **Ingress** (или Gateway), который реально принимает трафик с интернета на нужный домен;
- выбран способ challenge: **HTTP-01** (доступен порт 80 к solver) или **DNS-01** (например IAM + Route53, если зона в AWS).

Пока TLS только на **Mac/nginx** снаружи кластера — LE внутри кластера не обязателен: сначала cert-manager + `selfsigned` / свой CA для внутренних нужд; **ClusterIssuer** с `acme` добавь отдельным манифестом, когда будешь готов (часто начинают со **staging** Let’s Encrypt, чтобы не упираться в rate limits).
