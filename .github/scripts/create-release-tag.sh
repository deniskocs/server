#!/usr/bin/env bash
# Creates or moves a release git tag after a successful build and deploy PR.
# Usage: create-release-tag.sh <git-tag> <version> <new|retag> <service-label>
set -euo pipefail

GIT_TAG="${1:?git tag required}"
VERSION="${2:?version required}"
TAG_MODE="${3:?tag mode required (new or retag)}"
SERVICE_LABEL="${4:?service label required (e.g. llm-orchestrator-api)}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

MESSAGE="${SERVICE_LABEL} v${VERSION}"

case "$TAG_MODE" in
  new)
    if git rev-parse "$GIT_TAG" >/dev/null 2>&1; then
      echo "Git tag already exists: $GIT_TAG" >&2
      exit 1
    fi
    git tag -a "$GIT_TAG" -m "$MESSAGE"
    git push origin "$GIT_TAG"
    ;;
  retag)
    git tag -fa "$GIT_TAG" -m "$MESSAGE"
    git push -f origin "$GIT_TAG"
    ;;
  *)
    echo "Invalid tag mode: $TAG_MODE (expected new or retag)" >&2
    exit 1
    ;;
esac

echo "Git tag ${GIT_TAG} (${TAG_MODE})"
