# База знаний: репозиторий `server` (инфраструктура K8s и секреты)

Этот файл — **локальная вики в репозитории** (не MCP-вики). Сюда сведены решения и контекст по платформенному стеку в Kubernetes, Argo CD, cert-manager, External Secrets Operator и Bitwarden Secrets Manager.

---

## 1. Репозиторий и границы

| Что | Где |
|-----|-----|
| Репозиторий | `github.com:deniskocs/server` (локально `personal/server`) |
| Корень K8s-стека под Argo `server` | `infra/k8s/server/` — Kustomize + `helmCharts` |
| Описание приложения Argo CD `server` | `infra/k8s/platform/applications/server.yaml` |
| App-of-apps (корень платформы) | `infra/k8s/platform/applications/` + Terraform Helm `argocd-apps` |

Приложение **`server`** в Argo CD тянет **только** `path: infra/k8s/server`, `targetRevision: main`. Новые манифесты платформы в кластере добавляются в этот каталог и в `kustomization.yaml`.

`spec.destination.namespace: default` у Application **не** создаёт namespace для чартов вроде `cert-manager` / `external-secrets`: для них в манифестах явно заданы `metadata.namespace` и отдельные ресурсы `Namespace` с sync-wave.

---

## 2. Argo CD и Kustomize + Helm

- Для сборки Kustomize с чартами нужен флаг **`--enable-helm`**. В кластере это задано глобально для Argo CD (`kustomize.buildOptions` в values платформы).
- Локально: `kubectl kustomize infra/k8s/server --enable-helm` — в `PATH` должен быть **Helm** (Argo CD использует свой при рендере).

---

## 3. Порядок синхронизации (sync-wave)

Используется аннотация `argocd.argoproj.io/sync-wave` (меньше — раньше).

| Ресурс | Wave | Зачем |
|--------|------|--------|
| `Namespace` `cert-manager` | `-10` | Namespace до Helm chart cert-manager |
| `Namespace` `external-secrets` | `-8` | Namespace до Helm chart ESO |
| `ClusterIssuer` `selfsigned` | `10` | После поднятия cert-manager CRD/контроллера |

Helm-ресурсы без своей аннотации идут с дефолтным wave `0`. При включении **`bitwarden-sdk-server`** нужно заранее иметь TLS Secret (см. §6), иначе поды SDK не стартуют — при необходимости добавляют отдельные `Certificate` с wave **выше**, чем у Deployment SDK (например 15–20), либо выключают SDK до готовности Secret.

---

## 4. cert-manager

- Чарт в `kustomization.yaml`: Jetstack **cert-manager** `v1.20.2`, namespace **`cert-manager`**, `includeCRDs: true`, values — `cert-manager-values.yaml`.
- **`ClusterIssuer` `selfsigned`**: внутренние сертификаты без публичного DNS (сервисы внутри кластера, в т.ч. подготовка к TLS для внутренних компонентов).
- **Let’s Encrypt**: не внедряли до появления реального Ingress/Gateway и выбранного challenge (HTTP-01 / DNS-01). Staging ACME — разумный первый шаг из-за rate limits.

Подробности кратко: `infra/k8s/server/README.md` (секция cert-manager).

---

## 5. External Secrets Operator (ESO)

- Чарт: **external-secrets** `2.6.0`, repo `https://charts.external-secrets.io`, release **`external-secrets`**, namespace **`external-secrets`**, `includeCRDs: true`, values — `external-secrets-values.yaml`.
- В кластере: CRD **`ExternalSecret`**, **`SecretStore`**, **`ClusterSecretStore`** и др., контроллер, **webhook**.
- Подключение бэкендов (Vault, AWS SM, **Bitwarden Secrets Manager** и т.д.) — отдельными манифестами store + `ExternalSecret`. **Секреты и токены в git не коммитить**; в git — только ссылки на K8s `Secret` (или плейсхолдеры процесса), сами значения — bootstrap через `kubectl create secret`, Sealed Secrets, SOPS, секреты CI и т.п.

Официальный chart: [external-secrets/external-secrets](https://github.com/external-secrets/external-secrets).

---

## 6. Bitwarden Secrets Manager (BSM)

### 6.1. Что это

- **Bitwarden Secrets Manager** — облачный продукт Bitwarden (проекты, секреты, machine accounts, API). **Отдельного «сервера BSM» в Kubernetes нет** — в репо нет Helm chart «установить BSM».

### 6.2. Использование без синка в K8s

- CLI **`bws`**, токен **machine account** только в защищённом хранилище (CI secrets, локально).
- Документация: [Secrets Manager (Bitwarden Help)](https://bitwarden.com/help/secrets-manager/).

### 6.3. Использование через ESO (провайдер Bitwarden)

- В chart ESO есть опциональный подchart **`bitwarden-sdk-server`** (обёртка над Bitwarden Rust SDK для ESO). Сейчас в values: **`bitwarden-sdk-server.enabled: false`**.

**Почему выключен по умолчанию:** Deployment SDK монтирует Secret **`bitwarden-tls-certs`** в namespace **`external-secrets`** с ключами **`tls.crt`**, **`tls.key`**, **`ca.crt`**. Без этого Secret под не поднимется (FailedMount / CrashLoop).

**Когда можно включить `true`:** после появления в кластере указанного Secret с тремя ключами. У листового сертификата, подписанного только **`ClusterIssuer` `selfsigned`**, в Secret часто **нет** `ca.crt` в нужном виде; надёжная схема — короткий **CA** (Certificate с `isCA: true` + `Issuer`/`ClusterIssuer` типа **CA** в `external-secrets`), затем **Certificate** для DNS вида `bitwarden-sdk-server.external-secrets.svc.cluster.local`, Secret имя **`bitwarden-tls-certs`**.

Дальше в **`SecretStore`** / **`ClusterSecretStore`**: `bitwardenServerSDKURL` на сервис SDK (порт **9998**), `apiURL` / `identityURL` Bitwarden (или EU/self-hosted при необходимости), `organizationID`, `projectID`, `auth.secretRef` на K8s Secret с токеном machine account, `caProvider` или `caBundle` для доверия к TLS SDK.

Документация провайдера: [Bitwarden Secrets Manager — External Secrets](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/).

---

## 7. GitOps и секреты (правила)

1. В **git** не класть значения секретов, токены machine account, kubeconfig с учётками.
2. В git — манифесты **`ExternalSecret`**, **`SecretStore`** с `secretKeyRef` на уже существующие K8s Secret **или** зашифрованные слои (SOPS / Sealed Secrets), согласованные с командой.
3. **Bootstrap** токена в кластер — отдельная операция (ручная или CI с OIDC/secrets store).

---

## 8. Связанные пути в репозитории

```
infra/k8s/server/
  kustomization.yaml              # cert-manager + external-secrets
  cert-manager-values.yaml
  external-secrets-values.yaml    # installCRDs; bitwarden-sdk-server.enabled
  namespace-cert-manager.yaml
  namespace-external-secrets.yaml
  clusterissuer-selfsigned.yaml
  README.md                       # краткая инструкция по каталогу
infra/k8s/platform/applications/server.yaml
```

Короткий операционный README по каталогу: **`infra/k8s/server/README.md`**. Расширенная фиксация знаний — **этот файл (`WIKI-README.md`)**.

---

## 9. История решений (фиксация)

| Дата (контекст) | Решение |
|-----------------|---------|
| Платформа | Argo CD app-of-apps; приложение `server` деплоит `infra/k8s/server`. |
| TLS внутри кластера | cert-manager + `ClusterIssuer` `selfsigned`; LE отложен до Ingress/DNS. |
| Секреты для приложений | External Secrets Operator 2.6.0 в NS `external-secrets`; бэкенды подключаются отдельно. |
| Bitwarden SM | Облако + опционально ESO-провайдер; SDK server выключен до готовности `bitwarden-tls-certs`. |
| Argo sync ESO CRD | `ServerSideApply=true` + `ignoreDifferences` для `Deployment.status.terminatingReplicas` (см. §10). |

При смене версий chart или схемы bootstrap обновляй **§3–§6**, **§10** и таблицу в **§9**.

---

## 10. Argo CD: ошибка «metadata.annotations: Too long» на CRD ESO

**Симптом:** при sync приложения `server` падает применение CRD `clustersecretstores.external-secrets.io` / `secretstores.external-secrets.io` с текстом вроде `metadata.annotations: Too long: may not be more than 262144 bytes`.

**Причина:** у очень больших CRD client-side apply через Argo/kubectl накапливает данные в **annotations** и упирается в лимит Kubernetes **256 KiB** на весь объект `metadata.annotations`.

**Что сделано:** в `infra/k8s/platform/applications/server.yaml` в `syncPolicy.syncOptions` добавлено **`ServerSideApply=true`** — синк идёт через server-side apply, без раздувания annotations тем же механизмом.

**Если синк всё ещё падает:** проверь версию Argo CD (опция нужна с поддерживаемых релизов); запасной путь — ставить CRD ESO вне Argo (`kubectl apply --server-side -f …` из chart) и в `external-secrets-values.yaml` выставить `installCRDs: false`.

### Ошибка diff: `.status.terminatingReplicas: field not declared in schema`

**Симптом:** в UI или при sync: `Failed to compare desired state to live state` / `structured merge diff` / `terminatingReplicas` не объявлено в схеме.

**Причина:** в **новом Kubernetes** у `Deployment.status` появилось поле **`terminatingReplicas`**; встроенная OpenAPI-схема Argo CD (часто от более старого K8s) этого поля не знает — typed diff ломается.

**Что сделано:** в `Application` `server` в **`spec.ignoreDifferences`** для `apps/Deployment` добавлен jsonPointer **`/status/terminatingReplicas`**.

Долгосрочно полезно **обновить Argo CD** до версии с актуальной схемой под твой кластер.
