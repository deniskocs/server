#!/usr/bin/env bash
# Backup keycloak PVC data-keycloak-postgresql-0 (PostgreSQL logical dump via pg_dump).
set -euo pipefail

NAMESPACE="${NAMESPACE:-keycloak}"
POD="${POD:-keycloak-postgresql-0}"
CONTAINER="${CONTAINER:-postgresql}"
SECRET="${SECRET:-keycloak-secrets}"
SECRET_PASSWORD_KEY="${SECRET_PASSWORD_KEY:-password}"
DB_USER="${DB_USER:-keycloak}"
DB_NAME="${DB_NAME:-keycloak}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUT_DIR="${SCRIPT_DIR}/${STAMP}"
ARCHIVE="${OUT_DIR}/dump.dump"
META="${OUT_DIR}/meta.txt"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found" >&2
  exit 1
fi

kubectl -n "${NAMESPACE}" get pod "${POD}" >/dev/null

PASS="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath="{.data.${SECRET_PASSWORD_KEY}}" | base64 -d)"

mkdir -p "${OUT_DIR}"

echo "Backing up ${NAMESPACE}/${POD} db=${DB_NAME} -> ${OUT_DIR}"

kubectl -n "${NAMESPACE}" exec "${POD}" -c "${CONTAINER}" -- \
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
  echo "pod=${POD}"
  echo "container=${CONTAINER}"
  echo "db=${DB_NAME}"
  echo "db_user=${DB_USER}"
  echo "pvc=data-keycloak-postgresql-0"
  echo "format=pg_dump-Fc"
  echo "node=$(kubectl -n "${NAMESPACE}" get pod "${POD}" -o jsonpath='{.spec.nodeName}')"
  echo "archive=$(basename "${ARCHIVE}")"
  echo "archive_bytes=$(wc -c <"${ARCHIVE}" | tr -d ' ')"
  echo "kube_context=$(kubectl config current-context 2>/dev/null || true)"
  echo "cluster_server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
} >"${META}"

echo "Done:"
echo "  ${ARCHIVE}"
echo "  ${META}"
