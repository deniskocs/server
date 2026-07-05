# Bitwarden BSM — store bitwarden-cluster (platform)

`ClusterSecretStore` **`bitwarden-cluster`** — platform-секреты (Keycloak engine). Часть **`external-secrets/`** в server.

## BSM project (сейчас)

**Пока используется тот же project, что и `bitwarden-tzone`** (`projectID` = project tzone в BSM). Секреты Keycloak (`keycloak-admin-password`, `keycloak-db-password`) остаются там же — в Bitwarden ничего менять не нужно.

Позже можно завести отдельный BSM project **`cluster`**, перенести секреты и обновить `projectID` здесь и в `keycloak/external-secret-keycloak.yaml`.

| Имя в BSM | K8s Secret | Назначение |
|-----------|------------|------------|
| `huggingface-token` | `llm-orchestrator/huggingface-secrets` → `token` | Hugging Face API token (vLLM download, gated models) |

## K8s bootstrap (вне git)

```bash
kubectl create secret generic bitwarden-access-token \
  -n external-secrets \
  --from-literal=token='…'
```

## Проверка

```bash
kubectl describe clustersecretstore bitwarden-cluster
kubectl describe externalsecret keycloak -n keycloak
kubectl get secret keycloak-secrets -n keycloak
```
