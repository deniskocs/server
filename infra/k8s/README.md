# Серверный стек в Kubernetes

Манифесты, которые Argo CD синхронизирует **одним** приложением `server` (см. `infra/home-cluster/argocd/application.yaml`).

- Bootstrap Argo CD и регистрация Application `server` — `infra/home-cluster/argocd/` (см. README там).
- Подкаталоги (`cert-manager/`, `external-secrets/`, …) + записи в `kustomization.yaml`.

Порядок применения при необходимости задаётся аннотациями sync-wave Argo CD (`argocd.argoproj.io/sync-wave`).

Полная выжимка (вики в репозитории): [WIKI-README.md](../../../WIKI-README.md).

## cert-manager (Helm)

Каталог **`cert-manager/`**: Helm Jetstack, namespace, `ClusterIssuer` **`selfsigned`** и **`letsencrypt-prod`**.

Values — `cert-manager/cert-manager-values.yaml` (`crds.enabled: true`).

После установки **`selfsigned`** выпускает внутренние сертификаты (Bitwarden SDK и т.д.); **`letsencrypt-prod`** — публичный TLS через HTTP-01.

Локально: `kubectl kustomize infra/k8s --enable-helm` нужен **Helm** в `PATH`; в Argo CD Helm уже есть в `repo-server`.

Namespace **`cert-manager`** — `cert-manager/namespace-cert-manager.yaml` (sync-wave `-10`).

### Let's Encrypt (TZone staging)

Публичный TLS для staging — **cert-manager HTTP-01** (как **certbot webroot** на router): challenge на `:80` → nginx Mac → Traefik → solver Ingress.

| Файл | Назначение |
|------|------------|
| `cert-manager/clusterissuer-letsencrypt-prod.yaml` | Let's Encrypt (HTTP-01) |
| `helmchartconfig-traefik.yaml` | Traefik `:443` на ноде |

**AWS / Route53 не нужны** — DNS-01 только для wildcard `*.stage` без перечисления хостов.

**tzone repo:** `certificate-stage-t-zone-org.yaml` (SAN: stage, auth, tenant, darlings) + Ingress `websecure`.

**server repo:** `argocd/` — Argo CD `argo.chilik.net`; `keycloak/` — Keycloak `keycloak.chilik.net` (cert-manager + Ingress `websecure`, как learn-english).

**Router:** `stream :443` SNI → k3s для t-zone; на `:80` `/.well-known/acme-challenge/` для t-zone → `10.0.0.2:80`.

Новый тенант `{name}.stage.t-zone.org` → добавить в `dnsNames` Certificate и в `tls.hosts` Ingress, `argocd app sync tzone`.

### Let's Encrypt — общие заметки

ACME (Let’s Encrypt) требует:

- **Ingress** (или Gateway), принимающий трафик на домен;
- challenge: **HTTP-01** (порт 80 к solver) или **DNS-01** (Route53 для wildcard `*.stage`).

Пока TLS только на **Mac/nginx** для **chilik.net** — certbot webroot остаётся. Внутренние сертификаты — `selfsigned` / CA Bitwarden SDK.

## External Secrets Operator (Helm)

Каталог **`external-secrets/`**: Helm ESO, namespace, TLS для SDK (cert-manager), **`bitwarden/`** (`ClusterSecretStore`).

Chart: [external-secrets](https://github.com/external-secrets/external-secrets), values — `external-secrets/external-secrets-values.yaml` (`installCRDs: true`). Namespace — sync-wave `-8`.

В кластере: CRD `ExternalSecret`, `SecretStore`, `ClusterSecretStore` и контроллеры (включая webhook).

Подключение конкретных бэкендов (AWS Secrets Manager, Vault, **Bitwarden Secrets Manager** и т.д.) делается отдельными манифестами `ClusterSecretStore` / `SecretStore` и `ExternalSecret` в репозитории приложения или здесь — **токены и ключи в git не кладутся**, только ссылки на Kubernetes `Secret` с учётными данными.

### Bitwarden Secrets Manager + ESO

Подchart **`bitwarden-sdk-server`** включён (`external-secrets-values.yaml`); TLS для HTTPS выпускает **cert-manager**:

| Файл | Назначение |
|------|------------|
| `external-secrets/certificate-bitwarden-root-ca.yaml` | CA → Secret **`bitwarden-internal-ca`** (wave `15`) |
| `external-secrets/issuer-bitwarden-internal-ca.yaml` | **`Issuer`** CA (wave `16`) |
| `external-secrets/certificate-bitwarden-sdk-server-tls.yaml` | Secret **`bitwarden-tls-certs`** (wave `17`) |

У **Deployment** SDK аннотация **`argocd.argoproj.io/sync-wave: "20"`**, чтобы под стартовал после готовности Secret.

В **`SecretStore`** / **`ClusterSecretStore`**: `bitwardenServerSDKURL: https://bitwarden-sdk-server.external-secrets.svc.cluster.local:9998`, `caProvider` (или `caBundle`) на Secret **`bitwarden-tls-certs`**, ключ **`ca.crt`**. Токен **machine account** — в отдельном K8s Secret, не в git ([документация провайдера](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/)).

**Bootstrap токена** (один раз, вне git; вместо `…` подставь access token из Bitwarden → Machine account → Access tokens):

```bash
kubectl create secret generic bitwarden-access-token \
  -n external-secrets \
  --from-literal=token='…'
```

В `SecretStore` обычно указывают `auth.secretRef.credentials.name: bitwarden-access-token` и `key: token` (как в примерах ESO для Bitwarden).

### Bitwarden: project cluster (platform) и tzone (продукт)

- **`ClusterSecretStore` `bitwarden-cluster`** — `external-secrets/bitwarden/`: store platform в **server**; **пока тот же BSM project**, что tzone (ID совпадает).
- **`keycloak/`** — Keycloak admin/db через **bitwarden-cluster** (`external-secret-keycloak.yaml`).
- **`ClusterSecretStore` `bitwarden-tzone`** — репозиторий **tzone** (`deploy/k8s/bitwarden/`): секреты приложений и realm clients.
- ExternalSecret сервисов TZone — в **tzone** (`deploy/k8s/*/external-secret-*.yaml`).

Проверка: `kubectl describe clustersecretstore bitwarden-cluster` и `bitwarden-tzone`.

Подробнее project **cluster**: [`external-secrets/bitwarden/README.md`](external-secrets/bitwarden/README.md).

## Bitwarden Secrets Manager (сервис вне кластера)

**Bitwarden Secrets Manager** — это **облачный API и веб-консоль** Bitwarden. Отдельного деплоя «сервера BSM» в этом каталоге нет.

Без синхронизации в Kubernetes секреты из BSM удобно забирать через CLI **`bws`** в CI или локально ([документация](https://bitwarden.com/help/secrets-manager/)); токен machine account — только в защищённом хранилище CI или в `kubectl create secret`, не в git.

С **ESO** (см. выше) значения могут попадать в `Secret` в кластере через `ExternalSecret`, когда настроены **SecretStore** с токеном machine account и (для BSM) **`bitwardenServerSDKURL`** на SDK.

## Keycloak (Helm)

Всё platform Keycloak — каталог **`keycloak/`**: namespace, `ExternalSecret`, Helm `bitnami/keycloak` (PostgreSQL subchart), Certificate и Ingress для `keycloak.chilik.net`.

Пароли **не в git** — `keycloak/external-secret-keycloak.yaml` тянет из Bitwarden в Secret **`keycloak-secrets`** (sync-wave `19`). Chart — sync-wave `20`, Ingress — `21`.

### Секреты Keycloak в Bitwarden (project tzone, тот же что раньше)

Имена секретов без изменений (см. [`external-secrets/bitwarden/README.md`](external-secrets/bitwarden/README.md)):

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

### Доступ

| Куда | URL |
|------|-----|
| Admin Console (снаружи) | https://keycloak.chilik.net — `keycloak/ingress-keycloak.yaml`, `hostname` в `keycloak/keycloak-values.yaml` |
| Внутри кластера | `http://keycloak.keycloak.svc.cluster.local:80` |

Логин `admin`, пароль из Bitwarden (`keycloak-admin-password`).

Локально без Ingress:

```bash
kubectl port-forward svc/keycloak 8080:80 -n keycloak
```

Образы — `bitnamilegacy/*` (free Bitnami images переехали из `bitnami/*`).

### Realm `tzone`

**Не в этом репозитории.** Server ставит только платформенный Keycloak (Helm + секреты). Декларативный realm, clients и dev-user — Argo CD Application **`tzone`**, каталог `tzone/deploy/k8s/keycloak/` (источник: `services/keycloak/infra/realm/tzone-realm.json`).
