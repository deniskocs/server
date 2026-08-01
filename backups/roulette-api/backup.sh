#!/usr/bin/env bash
# Backup roulette-api PVC roulette-api-data (H2 files under /data).
# Scales Deployment to 0, copies via a temporary pod on the PVC node, then restores replicas.
set -euo pipefail

NAMESPACE="${NAMESPACE:-roulette-api}"
DEPLOYMENT="${DEPLOYMENT:-roulette-api}"
PVC="${PVC:-roulette-api-data}"
DATA_PATH="${DATA_PATH:-/data}"
COPY_IMAGE="${COPY_IMAGE:-busybox:1.36}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUT_DIR="${SCRIPT_DIR}/${STAMP}"
ARCHIVE="${OUT_DIR}/data.tar.gz"
META="${OUT_DIR}/meta.txt"
COPY_POD="roulette-api-backup-copy"
SCALED_DOWN=0
PREV_REPLICAS=1

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found" >&2
  exit 1
fi

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

kubectl -n "${NAMESPACE}" get deploy "${DEPLOYMENT}" >/dev/null
kubectl -n "${NAMESPACE}" get pvc "${PVC}" >/dev/null

NODE="$(kubectl -n "${NAMESPACE}" get pvc "${PVC}" -o jsonpath='{.metadata.annotations.volume\.kubernetes\.io/selected-node}')"
if [[ -z "${NODE}" ]]; then
  echo "PVC ${PVC} has no volume.kubernetes.io/selected-node annotation" >&2
  exit 1
fi

PREV_REPLICAS="$(kubectl -n "${NAMESPACE}" get deploy "${DEPLOYMENT}" -o jsonpath='{.spec.replicas}')"
PREV_REPLICAS="${PREV_REPLICAS:-1}"

mkdir -p "${OUT_DIR}"

echo "Scaling ${DEPLOYMENT} to 0 for consistent H2 backup (node=${NODE})..."
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

echo "Backing up ${NAMESPACE}/${COPY_POD}:${DATA_PATH} -> ${OUT_DIR}"
kubectl -n "${NAMESPACE}" exec "${COPY_POD}" -- tar -C "${DATA_PATH}" -czf - . >"${ARCHIVE}"
kubectl -n "${NAMESPACE}" delete pod "${COPY_POD}" --wait=true >/dev/null

{
  echo "timestamp=${STAMP}"
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "namespace=${NAMESPACE}"
  echo "deployment=${DEPLOYMENT}"
  echo "pvc=${PVC}"
  echo "data_path=${DATA_PATH}"
  echo "format=tar-gz"
  echo "engine=h2"
  echo "node=${NODE}"
  echo "archive=$(basename "${ARCHIVE}")"
  echo "archive_bytes=$(wc -c <"${ARCHIVE}" | tr -d ' ')"
  echo "kube_context=$(kubectl config current-context 2>/dev/null || true)"
  echo "cluster_server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
} >"${META}"

echo "Done:"
echo "  ${ARCHIVE}"
echo "  ${META}"
