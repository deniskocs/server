#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"
PY="${VENV}/bin/python"
REQ="${ROOT}/requirements.txt"
STAMP="${VENV}/.requirements_installed"

if [[ ! -x "${PY}" ]]; then
  python3 -m venv "${VENV}"
fi

if [[ ! -f "${STAMP}" ]] || [[ "${REQ}" -nt "${STAMP}" ]]; then
  "${PY}" -m pip install -q -r "${REQ}"
  touch "${STAMP}"
fi

exec "${PY}" "${ROOT}/server.py" "$@"
