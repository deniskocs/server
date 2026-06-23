# Argo CD — Application server

`application.yaml` — Application **`server`**, деплой `infra/k8s/server` (cert-manager, ESO, Keycloak, Traefik…).

По аналогии с `tzone/deploy/argocd/` и `learn-english-backend/infra/argocd/`: каталог **рядом** с k8s-манифестами, не внутри sync path.

Bootstrap Argo CD (Helm): Terraform `infra/home-cluster` (`argocd.tf` + `values/argocd.yaml`).

## Первичная регистрация (один раз)

1. После `terraform apply` в `infra/home-cluster`.
2. Репозиторий `server` в Argo CD (SSH).
3. С Mac:

```bash
scp infra/k8s/argocd/application.yaml USER@NODE:/tmp/server-application.yaml
ssh -t USER@NODE 'sudo k3s kubectl apply -f /tmp/server-application.yaml'
```

## Миграция с app-of-apps (platform-root)

1. Push server с `infra/k8s/argocd/` и без `argocd-apps`.
2. `terraform apply` в `infra/home-cluster` — удалит `argocd-apps` и `platform-root`.
3. При необходимости снова apply `application.yaml` (если `server` пропал после prune).
4. `argocd app sync server`

## Изменения

- **`infra/k8s/server/`** — push, Argo sync сам.
- **`application.yaml`** (редко) — scp + apply.

```bash
argocd app sync server
```
