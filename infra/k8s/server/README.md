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

### Let's Encrypt (TZone staging)

Публичный TLS для staging — **cert-manager HTTP-01** (как **certbot webroot** на router): challenge на `:80` → nginx Mac → Traefik → solver Ingress.

| Файл | Назначение |
|------|------------|
| `clusterissuer-letsencrypt-prod.yaml` | Let's Encrypt (HTTP-01) |
| `helmchartconfig-traefik.yaml` | Traefik `:443` на ноде |

**AWS / Route53 не нужны** — DNS-01 только для wildcard `*.stage` без перечисления хостов.

**tzone repo:** `certificate-stage-t-zone-org.yaml` (явные SAN: stage, auth, tenant, darlings, argo) + Ingress `websecure`. Argo CD — `argo.stage.t-zone.org`.

**Router:** `stream :443` SNI → k3s для t-zone; на `:80` `/.well-known/acme-challenge/` для t-zone → `10.0.0.2:80`.

Новый тенант `{name}.stage.t-zone.org` → добавить в `dnsNames` Certificate и в `tls.hosts` Ingress, `argocd app sync tzone`.

### Let's Encrypt — общие заметки

ACME (Let’s Encrypt) требует:

- **Ingress** (или Gateway), принимающий трафик на домен;
- challenge: **HTTP-01** (порт 80 к solver) или **DNS-01** (Route53 для wildcard `*.stage`).

Пока TLS только на **Mac/nginx** для **chilik.net** — certbot webroot остаётся. Внутренние сертификаты — `selfsigned` / CA Bitwarden SDK.

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

### Bitwarden: проект tzone

- **`ClusterSecretStore` `bitwarden-tzone`** — в репозитории **tzone** (`deploy/k8s/bitwarden/`): привязка к project tzone в BSM; токен и CA — здесь, в namespace `external-secrets`.
- **`external-secret-keycloak.yaml`** — admin/db Keycloak из BSM project tzone (store выше).
- ExternalSecret сервисов TZone — в **tzone** (`deploy/k8s/*/external-secret-*.yaml`).

Проверка store: `kubectl describe clustersecretstore bitwarden-tzone`.

## Bitwarden Secrets Manager (сервис вне кластера)

**Bitwarden Secrets Manager** — это **облачный API и веб-консоль** Bitwarden. Отдельного деплоя «сервера BSM» в этом каталоге нет.

Без синхронизации в Kubernetes секреты из BSM удобно забирать через CLI **`bws`** в CI или локально ([документация](https://bitwarden.com/help/secrets-manager/)); токен machine account — только в защищённом хранилище CI или в `kubectl create secret`, не в git.

С **ESO** (см. выше) значения могут попадать в `Secret` в кластере через `ExternalSecret`, когда настроены **SecretStore** с токеном machine account и (для BSM) **`bitwardenServerSDKURL`** на SDK.

## Keycloak (Helm)

Один release `bitnami/keycloak` в `kustomization.yaml` (PostgreSQL — subchart), values — `keycloak-values.yaml`.

Пароли **не в git** — `ExternalSecret` **`external-secret-keycloak.yaml`** тянет из Bitwarden в Secret **`keycloak-secrets`** (namespace `keycloak`, sync-wave `2`). Chart Keycloak — sync-wave `3`.

### Секреты в Bitwarden (проект tzone)

Создайте в [Bitwarden Secrets Manager](https://vault.bitwarden.com) два секрета (имена **точно** такие):

| Имя в BSM | Ключ в K8s Secret | Назначение |
|-----------|-------------------|------------|
| `keycloak-admin-password` | `admin-password` | Admin Console (`auth.adminUser=admin`) |
| `keycloak-db-password` | `password`, `postgres-password` | PostgreSQL + пользователь БД `keycloak` |

Можно перенести значения из GitHub secrets staging: `TZONE_STAGING_KEYCLOAK_ADMIN_PASSWORD`, `TZONE_STAGING_KEYCLOAK_DB_PASSWORD`.

Проверка после sync:

```bash
kubectl describe externalsecret keycloak -n keycloak
kubectl get secret keycloak-secrets -n keycloak
```

### Доступ к Admin Console

```bash
kubectl get pods -n keycloak
kubectl port-forward --address 0.0.0.0 svc/keycloak 8080:80 -n keycloak
```

→ http://localhost:8080 (или IP мастер-ноды:8080) — логин `admin`, пароль из Bitwarden.

Внутри кластера: `http://keycloak.keycloak.svc.cluster.local:80`.

Образы — `bitnamilegacy/*` (free Bitnami images переехали из `bitnami/*`).

### Realm `tzone`

**Не в этом репозитории.** Server ставит только платформенный Keycloak (Helm + секреты). Декларативный realm, clients и dev-user — Argo CD Application **`tzone`**, каталог `tzone/deploy/k8s/keycloak/` (источник: `services/keycloak/infra/realm/tzone-realm.json`).
