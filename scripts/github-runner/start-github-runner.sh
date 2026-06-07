#!/usr/bin/env bash
# Запуск self-hosted GitHub Actions runner на Mac Studio (пользователь denischilik).
# Вызывается из .github/workflows/start-github-runner.yaml по SSH.
set -euo pipefail

RUNNER_USER="${RUNNER_USER:-denischilik}"
RUNNER_DIR="${RUNNER_DIR:-/Users/${RUNNER_USER}/actions-runner}"
RUNNER_HOME="/Users/${RUNNER_USER}"

run_as_runner_user() {
  if [[ "$(whoami)" == "${RUNNER_USER}" ]]; then
    "$@"
  else
    sudo -u "${RUNNER_USER}" "$@"
  fi
}

if [[ ! -d "${RUNNER_DIR}" ]]; then
  echo "ERROR: actions-runner not found at ${RUNNER_DIR}"
  echo "Create runner: GitHub repo → Settings → Actions → Runners → New self-hosted runner"
  echo "Then: mkdir -p ${RUNNER_DIR}, extract tarball, ./config.sh, ./svc.sh install"
  exit 1
fi

if [[ ! -x "${RUNNER_DIR}/svc.sh" ]]; then
  echo "ERROR: ${RUNNER_DIR}/svc.sh not found or not executable"
  exit 1
fi

# Старый LaunchAgent мог ссылаться на удалённый путь и крутиться с ENOENT.
OLD_PLIST="${RUNNER_HOME}/Library/LaunchAgents/actions.runner.deniskocs-learn-english-flutter.Deniss-Mac-Studio.plist"
if [[ -f "${OLD_PLIST}" ]]; then
  OLD_WD="$(run_as_runner_user plutil -extract WorkingDirectory raw "${OLD_PLIST}" 2>/dev/null || true)"
  if [[ -n "${OLD_WD}" && "${OLD_WD}" != "${RUNNER_DIR}" && ! -d "${OLD_WD}" ]]; then
    echo "Unloading stale LaunchAgent (missing ${OLD_WD})..."
    run_as_runner_user launchctl bootout "gui/$(id -u "${RUNNER_USER}")" "${OLD_PLIST}" 2>/dev/null || true
    run_as_runner_user rm -f "${OLD_PLIST}"
  fi
fi

echo "Starting runner in ${RUNNER_DIR}..."
run_as_runner_user bash -c "cd '${RUNNER_DIR}' && ./svc.sh start"
run_as_runner_user bash -c "cd '${RUNNER_DIR}' && ./svc.sh status" || true

if run_as_runner_user pgrep -fl 'Runner\.Listener' >/dev/null 2>&1; then
  echo "OK: Runner.Listener is running"
else
  echo "ERROR: Runner.Listener process not found after start"
  tail -20 "${RUNNER_HOME}/Library/Logs/actions.runner."*/stdout.log 2>/dev/null || true
  exit 1
fi
