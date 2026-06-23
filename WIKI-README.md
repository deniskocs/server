# База знаний: репозиторий `server` (инфраструктура K8s и секреты)

Этот файл — **локальная вики в репозитории** (не MCP-вики). Сюда сведены решения и контекст по платформенному стеку в Kubernetes, Argo CD, cert-manager, External Secrets Operator и Bitwarden Secrets Manager.

---

## 1. Репозиторий и границы

| Что | Где |
|-----|-----|
| Репозиторий | `github.com:deniskocs/server` (локально `personal/server`) |
| Корень K8s-стека под Argo `server` | `infra/k8s/server/` — Kustomize + `helmCharts` |
| Описание приложения Argo CD `server` | `infra/k8s/argocd/application.yaml` |
| Bootstrap Argo CD (Terraform) | `infra/k8s/platform/` — Helm `argo-cd`, values `values/argocd.yaml` |

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
| `Certificate` `bitwarden-root-ca` | `15` | CA для цепочки TLS SDK |
| `Issuer` `bitwarden-internal-ca` | `16` | CA Issuer (Secret из предыдущего шага) |
| `Certificate` `bitwarden-sdk-server-tls` | `17` | Secret **`bitwarden-tls-certs`** для SDK |
| `Deployment` bitwarden-sdk-server | `20` | Аннотация в values; после готовности TLS Secret |

Helm-ресурсы без своей аннотации идут с дефолтным wave `0` (в т.ч. основной контроллер ESO). Подchart **bitwarden-sdk-server** откладывается wave `20`, чтобы `bitwarden-tls-certs` уже существовал.

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

- Подchart **`bitwarden-sdk-server`** включён в `external-secrets-values.yaml`; TLS — манифесты **`certificate-bitwarden-root-ca.yaml`**, **`issuer-bitwarden-internal-ca.yaml`**, **`certificate-bitwarden-sdk-server-tls.yaml`** (waves 15→17, Deployment SDK wave 20).
- Secret **`bitwarden-tls-certs`** содержит **`tls.crt`**, **`tls.key`**, **`ca.crt`** для HTTPS SDK.
- В **`SecretStore`** / **`ClusterSecretStore`**: `bitwardenServerSDKURL: https://bitwarden-sdk-server.external-secrets.svc.cluster.local:9998`, `caProvider` на `bitwarden-tls-certs` / `ca.crt`, плюс `organizationID`, `projectID`, `auth.secretRef` на Secret с токеном machine account (bootstrap вне git).
- **`ClusterSecretStore` `bitwarden-cluster`** — **server**, `infra/k8s/server/bitwarden/` (platform; **пока тот же BSM project ID**, что tzone).
- **`ClusterSecretStore` `bitwarden-tzone`** — репозиторий **tzone**, `deploy/k8s/bitwarden/` (project **tzone**): секреты приложений. Для **`remoteRef.key`** по **имени** (не UUID) обязателен **`remoteRef.property`** = **project ID** ([правила провайдера](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/)); если **key** — UUID секрета, `property` не нужен.

**Bootstrap токена machine account** (вне репозитория; подставь реальный token вместо `…`):

```bash
kubectl create secret generic bitwarden-access-token \
  -n external-secrets \
  --from-literal=token='…'
```

Имя Secret и ключ должны совпасть с `auth.secretRef` в `SecretStore` (часто Secret `bitwarden-access-token`, ключ `token`).

Документация провайдера: [Bitwarden Secrets Manager — External Secrets](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/).

---

## 7. GitOps и секреты (правила)

1. В **git** не класть значения секретов, токены machine account, kubeconfig с учётками.
2. В git — манифесты **`ExternalSecret`**, **`SecretStore`** с `secretKeyRef` на уже существующие K8s Secret **или** зашифрованные слои (SOPS / Sealed Secrets), согласованные с командой.
3. **Bootstrap** токена в кластер — отдельная операция (ручная или CI с OIDC/secrets store), например:

```bash
kubectl create secret generic bitwarden-access-token \
  -n external-secrets \
  --from-literal=token='…'
```

---

## 8. Связанные пути в репозитории

```
infra/k8s/server/
  kustomization.yaml              # cert-manager + external-secrets
  cert-manager-values.yaml
  external-secrets-values.yaml    # installCRDs; bitwarden-sdk-server + sync-wave
  certificate-bitwarden-root-ca.yaml
  issuer-bitwarden-internal-ca.yaml
  certificate-bitwarden-sdk-server-tls.yaml
  external-secret-keycloak.yaml
  namespace-cert-manager.yaml
  namespace-external-secrets.yaml
  clusterissuer-selfsigned.yaml
  README.md                       # краткая инструкция по каталогу
infra/k8s/argocd/application.yaml
```

Короткий операционный README по каталогу: **`infra/k8s/server/README.md`**. Расширенная фиксация знаний — **этот файл (`WIKI-README.md`)**.

---

## 9. История решений (фиксация)

| Дата (контекст) | Решение |
|-----------------|---------|
| Платформа | Terraform ставит Argo CD; Application `server` self-register из `infra/k8s/argocd/`; деплой `infra/k8s/server`. |
| TLS внутри кластера | cert-manager + `ClusterIssuer` `selfsigned`; LE отложен до Ingress/DNS. |
| Секреты для приложений | External Secrets Operator 2.6.0 в NS `external-secrets`; бэкенды подключаются отдельно. |
| Bitwarden SM / SDK | Подchart `bitwarden-sdk-server` + TLS cert-manager (`bitwarden-tls-certs`, CA в NS `external-secrets`); токен MA вне git. |
| Argo sync ESO CRD | `ServerSideApply=true` + аннотация `compare-options: ServerSideDiff=true` на `Application` `server` (см. §10). |

При смене версий chart или схемы bootstrap обновляй **§3–§7**, **§10** и таблицу в **§9**.

---

## 10. Argo CD: ошибка «metadata.annotations: Too long» на CRD ESO

**Симптом:** при sync приложения `server` падает применение CRD `clustersecretstores.external-secrets.io` / `secretstores.external-secrets.io` с текстом вроде `metadata.annotations: Too long: may not be more than 262144 bytes`.

**Причина:** у очень больших CRD client-side apply через Argo/kubectl накапливает данные в **annotations** и упирается в лимит Kubernetes **256 KiB** на весь объект `metadata.annotations`.

**Что сделано:** в `infra/k8s/argocd/application.yaml` в `syncPolicy.syncOptions` добавлено **`ServerSideApply=true`** — синк идёт через server-side apply, без раздувания annotations тем же механизмом.

**Если синк всё ещё падает:** проверь версию Argo CD (опция нужна с поддерживаемых релизов); запасной путь — ставить CRD ESO вне Argo (`kubectl apply --server-side -f …` из chart) и в `external-secrets-values.yaml` выставить `installCRDs: false`.

### Ошибка diff: `.status.terminatingReplicas: field not declared in schema`

**Симптом:** в UI или при sync: `Failed to compare desired state to live state` / `structured merge diff` / `terminatingReplicas` не объявлено в схеме.

**Причина:** при **`ServerSideApply=true`** Argo по умолчанию использует **structured-merge diff** и **встроенную** OpenAPI-схему (часто старше твоего API-сервера). У `Deployment.status` в новом Kubernetes есть поля, которых нет в этой схеме (например **`terminatingReplicas`**) — разбор live-объекта падает с `field not declared in schema`.

**Правильный обход (не костыль):** аннотация на `Application` **`server`**: **`argocd.argoproj.io/compare-options: ServerSideDiff=true`** — сравнение через server-side diff вместо structured-merge при SSA, см. [Diff strategies](https://argo-cd.readthedocs.io/en/stable/user-guide/diff-strategies/). Это ровно тот сценарий, для которого Argo выделил отдельную стратегию.

**Долгосрочно:** обновлять Argo CD до версии с актуальной схемой под твой Kubernetes — тогда меньше расхождений с API в целом.

**Не рекомендуется** маскировать это через `ignoreDifferences` по полям status: это скрывает симптомы и не чинит несовпадение схемы для structured-merge.

**Если с `ServerSideDiff` появятся другие ошибки** (редко — баги dry-run на экзотических CR): обнови Argo CD до свежего патча или обсуждай fallback с командой.
