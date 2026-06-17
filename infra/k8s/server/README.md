# Серверный стек в Kubernetes

Сюда складываются манифесты, которые Argo CD синхронизирует **одним** приложением `server` (см. `infra/k8s/platform/applications/server.yaml`).

- Верхний уровень app-of-apps: только короткие `Application` в `infra/k8s/platform/applications/` (`tzone`, `server`).
- Всё содержимое деплоя из этого репозитория — под `infra/k8s/server/` (подкаталоги + записи в `kustomization.yaml`).

Порядок применения при необходимости задаётся аннотациями sync-wave Argo CD (`argocd.argoproj.io/sync-wave`).

## cert-manager (Helm)

Ставится через [helmCharts](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/helmcharts/) в `kustomization.yaml`, значения — `cert-manager-values.yaml` (`crds.enabled: true`).

После установки создаётся `ClusterIssuer` **`selfsigned`** — им можно выпускать внутренние сертификаты (сервисы внутри кластера без публичного DNS).

Локально: `kubectl kustomize infra/k8s/server --enable-helm` нужен **Helm** в `PATH`; в Argo CD Helm уже есть в `repo-server`.

Namespace **`cert-manager`** задаётся явным манифестом (`namespace-cert-manager.yaml`, sync-wave `-10`): опция `CreateNamespace` у Application `server` относится только к `spec.destination.namespace`, а не к произвольным namespace из чарта.

### Let's Encrypt — не сразу

ACME (Let’s Encrypt) имеет смысл подключать, когда:

- есть **Ingress** (или Gateway), который реально принимает трафик с интернета на нужный домен;
- выбран способ challenge: **HTTP-01** (доступен порт 80 к solver) или **DNS-01** (например IAM + Route53, если зона в AWS).

Пока TLS только на **Mac/nginx** снаружи кластера — LE внутри кластера не обязателен: сначала cert-manager + `selfsigned` / свой CA для внутренних нужд; **ClusterIssuer** с `acme` добавь отдельным манифестом, когда будешь готов (часто начинают со **staging** Let’s Encrypt, чтобы не упираться в rate limits).

## External Secrets Operator (Helm)

Ставится вторым чартом в `kustomization.yaml` ([chart](https://github.com/external-secrets/external-secrets)), namespace **`external-secrets`** — `namespace-external-secrets.yaml` (sync-wave `-8`, после `cert-manager` ns `-10`).

Значения: `external-secrets-values.yaml` (`installCRDs: true`). В кластере появятся CRD `ExternalSecret`, `SecretStore`, `ClusterSecretStore` и контроллеры (включая webhook).

Подключение конкретных бэкендов (AWS Secrets Manager, Vault, **Bitwarden Secrets Manager** и т.д.) делается отдельными манифестами `ClusterSecretStore` / `SecretStore` и `ExternalSecret` в репозитории приложения или здесь — **токены и ключи в git не кладутся**, только ссылки на Kubernetes `Secret` с учётными данными.

### Bitwarden Secrets Manager + ESO

Провайдер BSM в ESO опирается на подchart **`bitwarden-sdk-server`** (сейчас `enabled: false` в `external-secrets-values.yaml`). У сервера SDK **обязателен HTTPS**; в Secret `bitwarden-tls-certs` в namespace `external-secrets` должны быть ключи **`tls.crt`**, **`tls.key`** и **`ca.crt`** (см. [документацию провайдера](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/)).

Надёжный способ получить `ca.crt` у листового сертификата — выпуск через **CA Issuer** в том же namespace (короткий CA из `ClusterIssuer` `selfsigned`, затем `Issuer` с `spec.ca.secretName`, затем `Certificate` для `bitwarden-sdk-server…svc`). После появления Secret включи `bitwarden-sdk-server.enabled: true` и задеплой; в `SecretStore` укажи `bitwardenServerSDKURL` на сервис chart (порт **9998**) и `caProvider` / `caBundle` на тот же CA.

Токен **machine account** Bitwarden по-прежнему создаётся вручную и кладётся в Kubernetes `Secret` (bootstrap вне git).

## Bitwarden Secrets Manager (сервис вне кластера)

**Bitwarden Secrets Manager** — это **облачный API и веб-консоль** Bitwarden. Отдельного деплоя «сервера BSM» в этом каталоге нет.

Без синхронизации в Kubernetes секреты из BSM удобно забирать через CLI **`bws`** в CI или локально ([документация](https://bitwarden.com/help/secrets-manager/)); токен machine account — только в защищённом хранилище CI или в `kubectl create secret`, не в git.

С **ESO** (см. выше) значения могут попадать в `Secret` в кластере через `ExternalSecret`, когда настроены store и (для BSM) `bitwarden-sdk-server` + TLS.
