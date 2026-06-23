# Argo CD — bootstrap (home-cluster)

Helm values и регистрация Application **`server`**. Не путать с **`infra/k8s/argocd/`** — там Ingress и Certificate для `argo.chilik.net` (GitOps sync path).

| Файл | Кто применяет |
|------|----------------|
| `values.yaml` | Terraform `argocd.tf` (`helm_release argocd`) |
| `application.yaml` | Одноразовый `kubectl apply` после `terraform apply` |

`application.yaml` деплоит `infra/k8s` (cert-manager, ESO, Keycloak, Traefik…).

По аналогии с `tzone/deploy/argocd/` и `learn-english-backend/infra/argocd/`.

## Первичная регистрация (один раз)

1. `terraform apply` в `infra/home-cluster`.
2. Репозиторий `server` в Argo CD (SSH).
3. С Mac:

```bash
scp infra/home-cluster/argocd/application.yaml USER@NODE:/tmp/server-application.yaml
ssh -t USER@NODE 'sudo k3s kubectl apply -f /tmp/server-application.yaml'
```

## Миграция с app-of-apps (platform-root)

1. Push server с `infra/home-cluster/argocd/` и без `argocd-apps`.
2. `terraform apply` в `infra/home-cluster` — удалит `argocd-apps` и `platform-root`.
3. При необходимости снова apply `application.yaml` (если `server` пропал после prune).
4. `argocd app sync server`

## Изменения

- **`values.yaml`** — `terraform apply` в `infra/home-cluster`.
- **`infra/k8s/`** — push, Argo sync сам.
- **`application.yaml`** (редко) — scp + apply.

```bash
argocd app sync server
```
