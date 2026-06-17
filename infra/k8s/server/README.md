# Серверный стек в Kubernetes

Сюда складываются манифесты, которые Argo CD синхронизирует **одним** приложением `server` (см. `infra/k8s/platform/applications/server.yaml`).

- Верхний уровень app-of-apps: только короткие `Application` в `infra/k8s/platform/applications/` (`tzone`, `server`).
- Всё содержимое деплоя из этого репозитория — под `infra/k8s/server/` (подкаталоги + записи в `kustomization.yaml`).

Порядок применения при необходимости задаётся аннотациями sync-wave Argo CD (`argocd.argoproj.io/sync-wave`).

Полная выжимка (вики в репозитории): [WIKI-README.md](../../../WIKI-README.md).

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

Подchart **`bitwarden-sdk-server`** включён (`external-secrets-values.yaml`); TLS для HTTPS выпускает **cert-manager** в namespace `external-secrets`:

| Файл | Назначение |
|------|------------|
| `certificate-bitwarden-root-ca.yaml` | CA (`Certificate` `bitwarden-root-ca` → Secret **`bitwarden-internal-ca`**, wave `15`) |
| `issuer-bitwarden-internal-ca.yaml` | **`Issuer`** CA, ссылается на тот Secret (wave `16`) |
| `certificate-bitwarden-sdk-server-tls.yaml` | Листовой сертификат для `bitwarden-sdk-server…svc` → Secret **`bitwarden-tls-certs`** с `tls.crt`, `tls.key`, `ca.crt` (wave `17`) |

У **Deployment** SDK аннотация **`argocd.argoproj.io/sync-wave: "20"`**, чтобы под стартовал после готовности Secret.

В **`SecretStore`** / **`ClusterSecretStore`**: `bitwardenServerSDKURL: https://bitwarden-sdk-server.external-secrets.svc.cluster.local:9998`, `caProvider` (или `caBundle`) на Secret **`bitwarden-tls-certs`**, ключ **`ca.crt`**. Токен **machine account** — в отдельном K8s Secret, не в git ([документация провайдера](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/)).

**Bootstrap токена** (один раз, вне git; вместо `…` подставь access token из Bitwarden → Machine account → Access tokens):

```bash
kubectl create secret generic bitwarden-access-token \
  -n external-secrets \
  --from-literal=token='…'
```

В `SecretStore` обычно указывают `auth.secretRef.credentials.name: bitwarden-access-token` и `key: token` (как в примерах ESO для Bitwarden).

### Bitwarden: проект tzone в репозитории

- **`secretstore-bitwarden-tzone.yaml`** — `SecretStore` `bitwarden-tzone` (org/project из Bitwarden US cloud; EU — поменяй `apiURL` / `identityURL`).
- **`external-secret-bitwarden-tzone.yaml`** — тянет один ключ в Secret **`tzone-sm-secrets`**. В **`remoteRef.key`** — имя или UUID секрета в BSM. Если **key — не UUID**, по [доке ESO](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/) обязателен **`remoteRef.property`** = **project ID** (как в `SecretStore`); для поиска **по UUID** секрета `property` не указывай.

Проверка store: `kubectl describe secretstore bitwarden-tzone -n external-secrets`.

## Bitwarden Secrets Manager (сервис вне кластера)

**Bitwarden Secrets Manager** — это **облачный API и веб-консоль** Bitwarden. Отдельного деплоя «сервера BSM» в этом каталоге нет.

Без синхронизации в Kubernetes секреты из BSM удобно забирать через CLI **`bws`** в CI или локально ([документация](https://bitwarden.com/help/secrets-manager/)); токен machine account — только в защищённом хранилище CI или в `kubectl create secret`, не в git.

С **ESO** (см. выше) значения могут попадать в `Secret` в кластере через `ExternalSecret`, когда настроены **SecretStore** с токеном machine account и (для BSM) **`bitwardenServerSDKURL`** на SDK.
