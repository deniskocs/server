#!/usr/bin/env bash
# Restore tzone PostgreSQL from a dated backup directory created by backup.sh.
#
# Usage:
#   ./restore.sh                         # latest backup in this folder
#   ./restore.sh 2026-08-01_144512       # specific stamp or path
#   ./restore.sh /full/path/to/backupdir
#
# WARNING: uses pg_restore --clean --if-exists (drops/recreates objects in the target DB).
set -euo pipefail

NAMESPACE="${NAMESPACE:-tzone}"
APP_LABEL="${APP_LABEL:-tenant-postgres}"
CONTAINER="${CONTAINER:-postgres}"
SECRET="${SECRET:-tenant-service-secrets}"
SECRET_PASSWORD_KEY="${SECRET_PASSWORD_KEY:-db-password}"
DB_USER="${DB_USER:-tenant}"
DB_NAME="${DB_NAME:-tenant}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found" >&2
  exit 1
fi

resolve_backup_dir() {
  local arg="${1:-}"
  if [[ -z "${arg}" ]]; then
    local latest
    latest="$(ls -1d "${SCRIPT_DIR}"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9] 2>/dev/null | sort | tail -n 1 || true)"
    if [[ -z "${latest}" ]]; then
      echo "No dated backup directories found in ${SCRIPT_DIR}" >&2
      exit 1
    fi
    printf '%s\n' "${latest}"
    return
  fi
  if [[ -d "${arg}" ]]; then
    printf '%s\n' "$(cd "${arg}" && pwd)"
    return
  fi
  if [[ -d "${SCRIPT_DIR}/${arg}" ]]; then
    printf '%s\n' "${SCRIPT_DIR}/${arg}"
    return
  fi
  echo "Backup dir not found: ${arg}" >&2
  exit 1
}

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

BACKUP_DIR="$(resolve_backup_dir "${1:-}")"
ARCHIVE="${BACKUP_DIR}/dump.dump"

if [[ ! -f "${ARCHIVE}" ]]; then
  echo "Missing archive: ${ARCHIVE}" >&2
  exit 1
fi

POD_NAME="$(resolve_pod)"
kubectl -n "${NAMESPACE}" get pod "${POD_NAME}" >/dev/null

PASS="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath="{.data.${SECRET_PASSWORD_KEY}}" | base64 -d)"

echo "Restoring ${ARCHIVE}"
echo "  -> ${NAMESPACE}/${POD_NAME} db=${DB_NAME}"
echo "WARNING: --clean --if-exists will drop/recreate objects in ${DB_NAME}"
read -r -p "Type 'yes' to continue: " confirm
if [[ "${confirm}" != "yes" ]]; then
  echo "Aborted"
  exit 1
fi

set +e
kubectl -n "${NAMESPACE}" exec -i "${POD_NAME}" -c "${CONTAINER}" -- \
  env PGPASSWORD="${PASS}" \
  pg_restore \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
  <"${ARCHIVE}"
rc=$?
set -e
# pg_restore: 0=ok, 1=warnings (часто после --clean на пустой/новой БД), >=2=ошибка
if [[ "${rc}" -ge 2 ]]; then
  echo "pg_restore failed with exit code ${rc}" >&2
  exit "${rc}"
fi
if [[ "${rc}" -eq 1 ]]; then
  echo "pg_restore finished with warnings (exit 1) — обычно ок"
fi

echo "Restore finished from ${BACKUP_DIR}"
