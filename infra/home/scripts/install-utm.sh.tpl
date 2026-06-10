#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

utm_cask="${utm_cask}"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found in PATH" >&2
  exit 1
fi

if [ -d "/Applications/UTM.app" ] || brew list --cask "$${utm_cask}" >/dev/null 2>&1; then
  echo "UTM is already installed"
else
  echo "Installing UTM via Homebrew..."
  brew install --cask "$${utm_cask}"
  echo "UTM installed"
fi
