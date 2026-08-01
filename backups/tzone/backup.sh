#!/usr/bin/env bash
# Backup tzone PVC tenant-postgres-data (PostgreSQL logical dump via pg_dump).
set -euo pipefail

NAMESPACE="${NAMESPACE:-tzone}"
APP_LABEL="${APP_LABEL:-tenant-postgres}"
CONTAINER="${CONTAINER:-postgres}"
SECRET="${SECRET:-tenant-service-secrets}"
SECRET_PASSWORD_KEY="${SECRET_PASSWORD_KEY:-db-password}"
DB_USER="${DB_USER:-tenant}"
DB_NAME="${DB_NAME:-tenant}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUT_DIR="${SCRIPT_DIR}/${STAMP}"
ARCHIVE="${OUT_DIR}/dump.dump"
META="${OUT_DIR}/meta.txt"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found" >&2
  exit 1
fi

resolve_pod() {
  if [[ -n "${POD:-}" ]]; then
    printf '%s\n' "${POD}"
    return
  fi
  local name
  name="$(kubectl -n "${NAMESPACE}" get pod -l "app=${APP_LABEL}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [[ -z "${name}" ]]; then
    echo "No running pod with label app=${APP_LABEL} in ${NAMESPACE}" >&2
    exit 1
  fi
  printf '%s\n' "${name}"
}

POD_NAME="$(resolve_pod)"
kubectl -n "${NAMESPACE}" get pod "${POD_NAME}" >/dev/null

PASS="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath="{.data.${SECRET_PASSWORD_KEY}}" | base64 -d)"

mkdir -p "${OUT_DIR}"

echo "Backing up ${NAMESPACE}/${POD_NAME} db=${DB_NAME} -> ${OUT_DIR}"

kubectl -n "${NAMESPACE}" exec "${POD_NAME}" -c "${CONTAINER}" -- \
  env PGPASSWORD="${PASS}" \
  pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -Fc \
    --no-owner \
    --no-acl \
  >"${ARCHIVE}"

{
  echo "timestamp=${STAMP}"
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "namespace=${NAMESPACE}"
  echo "pod=${POD_NAME}"
  echo "container=${CONTAINER}"
  echo "db=${DB_NAME}"
  echo "db_user=${DB_USER}"
  echo "pvc=tenant-postgres-data"
  echo "format=pg_dump-Fc"
  echo "node=$(kubectl -n "${NAMESPACE}" get pod "${POD_NAME}" -o jsonpath='{.spec.nodeName}')"
  echo "archive=$(basename "${ARCHIVE}")"
  echo "archive_bytes=$(wc -c <"${ARCHIVE}" | tr -d ' ')"
  echo "kube_context=$(kubectl config current-context 2>/dev/null || true)"
  echo "cluster_server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
} >"${META}"

echo "Done:"
echo "  ${ARCHIVE}"
echo "  ${META}"
