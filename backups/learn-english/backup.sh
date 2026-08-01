#!/usr/bin/env bash
# Backup learn-english PVC data-mongodb-0 (MongoDB logical dump via mongodump).
set -euo pipefail

NAMESPACE="${NAMESPACE:-learn-english}"
POD="${POD:-mongodb-0}"
CONTAINER="${CONTAINER:-mongodb}"
SECRET="${SECRET:-mongodb-credentials}"
AUTH_DB="${AUTH_DB:-raw-data}"
DB_NAME="${DB_NAME:-raw-data}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUT_DIR="${SCRIPT_DIR}/${STAMP}"
ARCHIVE="${OUT_DIR}/dump.archive.gz"
META="${OUT_DIR}/meta.txt"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found" >&2
  exit 1
fi

kubectl -n "${NAMESPACE}" get pod "${POD}" >/dev/null

USER="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath='{.data.username}' | base64 -d)"
PASS="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath='{.data.password}' | base64 -d)"

mkdir -p "${OUT_DIR}"

echo "Backing up ${NAMESPACE}/${POD} db=${DB_NAME} -> ${OUT_DIR}"

kubectl -n "${NAMESPACE}" exec "${POD}" -c "${CONTAINER}" -- \
  mongodump \
    --username="${USER}" \
    --password="${PASS}" \
    --authenticationDatabase="${AUTH_DB}" \
    --db="${DB_NAME}" \
    --gzip \
    --archive \
  >"${ARCHIVE}"

{
  echo "timestamp=${STAMP}"
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "namespace=${NAMESPACE}"
  echo "pod=${POD}"
  echo "container=${CONTAINER}"
  echo "db=${DB_NAME}"
  echo "auth_db=${AUTH_DB}"
  echo "pvc=data-mongodb-0"
  echo "node=$(kubectl -n "${NAMESPACE}" get pod "${POD}" -o jsonpath='{.spec.nodeName}')"
  echo "archive=$(basename "${ARCHIVE}")"
  echo "archive_bytes=$(wc -c <"${ARCHIVE}" | tr -d ' ')"
  echo "kube_context=$(kubectl config current-context 2>/dev/null || true)"
  echo "cluster_server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
} >"${META}"

echo "Done:"
echo "  ${ARCHIVE}"
echo "  ${META}"
