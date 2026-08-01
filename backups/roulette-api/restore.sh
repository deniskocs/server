#!/usr/bin/env bash
# Restore roulette-api H2 data from a dated backup directory created by backup.sh.
#
# Usage:
#   ./restore.sh                         # latest backup
#   ./restore.sh 2026-08-01_144512
#   ./restore.sh /full/path/to/backupdir
#
# WARNING: replaces all files under /data on the PVC.
set -euo pipefail

NAMESPACE="${NAMESPACE:-roulette-api}"
DEPLOYMENT="${DEPLOYMENT:-roulette-api}"
PVC="${PVC:-roulette-api-data}"
DATA_PATH="${DATA_PATH:-/data}"
COPY_IMAGE="${COPY_IMAGE:-busybox:1.36}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COPY_POD="roulette-api-restore-copy"
SCALED_DOWN=0
PREV_REPLICAS=1

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

cleanup() {
  local rc=$?
  kubectl -n "${NAMESPACE}" delete pod "${COPY_POD}" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  if [[ "${SCALED_DOWN}" == "1" ]]; then
    echo "Restoring ${DEPLOYMENT} replicas=${PREV_REPLICAS}"
    kubectl -n "${NAMESPACE}" scale "deploy/${DEPLOYMENT}" --replicas="${PREV_REPLICAS}" >/dev/null || true
  fi
  exit "${rc}"
}
trap cleanup EXIT

BACKUP_DIR="$(resolve_backup_dir "${1:-}")"
ARCHIVE="${BACKUP_DIR}/data.tar.gz"

if [[ ! -f "${ARCHIVE}" ]]; then
  echo "Missing archive: ${ARCHIVE}" >&2
  exit 1
fi

NODE="$(kubectl -n "${NAMESPACE}" get pvc "${PVC}" -o jsonpath='{.metadata.annotations.volume\.kubernetes\.io/selected-node}')"
if [[ -z "${NODE}" ]]; then
  echo "PVC ${PVC} has no volume.kubernetes.io/selected-node annotation" >&2
  exit 1
fi

PREV_REPLICAS="$(kubectl -n "${NAMESPACE}" get deploy "${DEPLOYMENT}" -o jsonpath='{.spec.replicas}')"
# If already scaled to 0 by the caller, still bring the app back up after restore.
if [[ -z "${PREV_REPLICAS}" || "${PREV_REPLICAS}" == "0" ]]; then
  PREV_REPLICAS=1
fi

echo "Restoring ${ARCHIVE}"
echo "  -> ${NAMESPACE} PVC ${PVC} on node ${NODE}"
echo "WARNING: all files under ${DATA_PATH} will be replaced"
read -r -p "Type 'yes' to continue: " confirm
if [[ "${confirm}" != "yes" ]]; then
  echo "Aborted"
  exit 1
fi

echo "Scaling ${DEPLOYMENT} to 0..."
kubectl -n "${NAMESPACE}" scale "deploy/${DEPLOYMENT}" --replicas=0
SCALED_DOWN=1
kubectl -n "${NAMESPACE}" wait --for=delete pod -l app=roulette-api --timeout=180s || true

kubectl -n "${NAMESPACE}" delete pod "${COPY_POD}" --ignore-not-found --wait=true >/dev/null 2>&1 || true

cat <<EOF | kubectl -n "${NAMESPACE}" apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${COPY_POD}
spec:
  restartPolicy: Never
  nodeSelector:
    kubernetes.io/hostname: ${NODE}
  containers:
    - name: copy
      image: ${COPY_IMAGE}
      command: ["sleep", "600"]
      volumeMounts:
        - name: data
          mountPath: ${DATA_PATH}
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: ${PVC}
EOF

kubectl -n "${NAMESPACE}" wait --for=condition=Ready "pod/${COPY_POD}" --timeout=120s

echo "Clearing ${DATA_PATH} and extracting archive..."
kubectl -n "${NAMESPACE}" exec "${COPY_POD}" -- \
  sh -c "find '${DATA_PATH}' -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
kubectl -n "${NAMESPACE}" exec -i "${COPY_POD}" -- tar -C "${DATA_PATH}" -xzf - <"${ARCHIVE}"
kubectl -n "${NAMESPACE}" exec "${COPY_POD}" -- ls -la "${DATA_PATH}"
kubectl -n "${NAMESPACE}" delete pod "${COPY_POD}" --wait=true >/dev/null

echo "Restore finished from ${BACKUP_DIR}"
