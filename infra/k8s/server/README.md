# Серверный стек в Kubernetes

Сюда складываются манифесты, которые Argo CD синхронизирует **одним** приложением `server` (см. `infra/k8s/platform/applications/server.yaml`).

- Верхний уровень app-of-apps: только короткие `Application` в `infra/k8s/platform/applications/` (`tzone`, `server`).
- Всё содержимое деплоя из этого репозитория — под `infra/k8s/server/` (подкаталоги + записи в `kustomization.yaml`).

Порядок применения при необходимости задаётся аннотациями sync-wave Argo CD (`argocd.argoproj.io/sync-wave`).
