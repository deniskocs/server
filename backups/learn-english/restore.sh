#!/usr/bin/env bash
# Restore learn-english MongoDB from a dated backup directory created by backup.sh.
#
# Usage:
#   ./restore.sh                         # latest backup in this folder
#   ./restore.sh 2026-08-01_144512       # specific stamp or path
#   ./restore.sh /full/path/to/backupdir
#
# WARNING: uses mongorestore --drop (replaces collections in the target DB).
set -euo pipefail

NAMESPACE="${NAMESPACE:-learn-english}"
POD="${POD:-mongodb-0}"
CONTAINER="${CONTAINER:-mongodb}"
SECRET="${SECRET:-mongodb-credentials}"
AUTH_DB="${AUTH_DB:-raw-data}"
DB_NAME="${DB_NAME:-raw-data}"

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

BACKUP_DIR="$(resolve_backup_dir "${1:-}")"
ARCHIVE="${BACKUP_DIR}/dump.archive.gz"

if [[ ! -f "${ARCHIVE}" ]]; then
  echo "Missing archive: ${ARCHIVE}" >&2
  exit 1
fi

kubectl -n "${NAMESPACE}" get pod "${POD}" >/dev/null

USER="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath='{.data.username}' | base64 -d)"
PASS="$(kubectl -n "${NAMESPACE}" get secret "${SECRET}" -o jsonpath='{.data.password}' | base64 -d)"

echo "Restoring ${ARCHIVE}"
echo "  -> ${NAMESPACE}/${POD} db=${DB_NAME}"
echo "WARNING: --drop will replace existing collections in ${DB_NAME}"
read -r -p "Type 'yes' to continue: " confirm
if [[ "${confirm}" != "yes" ]]; then
  echo "Aborted"
  exit 1
fi

kubectl -n "${NAMESPACE}" exec -i "${POD}" -c "${CONTAINER}" -- \
  mongorestore \
    --username="${USER}" \
    --password="${PASS}" \
    --authenticationDatabase="${AUTH_DB}" \
    --db="${DB_NAME}" \
    --drop \
    --gzip \
    --archive \
  <"${ARCHIVE}"

echo "Restore finished from ${BACKUP_DIR}"
