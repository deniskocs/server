#!/usr/bin/env bash
# Updates a k8s manifest image tag and opens a deploy PR (no direct push to main).
# Usage: open-deploy-pr.sh <service-slug> <manifest-path> <image-repo> <version> <git-tag> [current]
set -euo pipefail

SERVICE_SLUG="${1:?service slug required (e.g. llm-orchestrator-api)}"
MANIFEST="${2:?manifest path required}"
IMAGE_REPO="${3:?docker image repo required (e.g. deniskocs/llm-orchestrator-api)}"
VERSION="${4:?version required}"
GIT_TAG="${5:?git tag required (e.g. llm-orchestrator-api/v0.0.6)}"
BUMP="${6:-}"

IS_CURRENT=false
if [[ "$BUMP" == "current" ]]; then
  IS_CURRENT=true
fi

if [[ "$IS_CURRENT" == "true" ]]; then
  BRANCH="deploy/${SERVICE_SLUG}-${VERSION}-redeploy-${GITHUB_RUN_ID:-local}"
else
  BRANCH="deploy/${SERVICE_SLUG}-${VERSION}"
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git fetch origin main
git checkout main
git reset --hard origin/main
git checkout -b "$BRANCH"

if ! grep -q "${IMAGE_REPO}:" "$MANIFEST"; then
  echo "Image reference not found in $MANIFEST" >&2
  exit 1
fi

sed -i "s|\(${IMAGE_REPO}:\)[^ \"']*|\1${VERSION}|g" "$MANIFEST"

# Manifest уже на нужной версии (bootstrap или rebuild) — форсируем rollout через redeploy-at.
FORCE_REDEPLOY=false
if git diff --quiet "$MANIFEST"; then
  FORCE_REDEPLOY=true
  REDEPLOY_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if grep -q 'chilik.net/redeploy-at:' "$MANIFEST"; then
    sed -i "s|chilik.net/redeploy-at:.*|chilik.net/redeploy-at: \"${REDEPLOY_AT}\"|" "$MANIFEST"
  elif grep -q '^kind: Deployment$' "$MANIFEST"; then
    # Pod template annotation only — не трогаем labels/selector (иначе ломается YAML для kustomize).
    perl -i -0pe '
      s/(^kind: Deployment\n(?:.*\n)*?  template:\n    metadata:\n)(      labels:)/$1      annotations:\n        chilik.net\/redeploy-at: "'"${REDEPLOY_AT}"'"\n$2/m
    ' "$MANIFEST"
    if ! grep -q 'chilik.net/redeploy-at:' "$MANIFEST"; then
      echo "Cannot force redeploy: failed to add pod template annotation in ${MANIFEST}." >&2
      exit 1
    fi
  else
    echo "Cannot force redeploy: manifest already at ${VERSION} and no Deployment template to annotate." >&2
    exit 1
  fi
fi

if git diff --quiet "$MANIFEST"; then
  echo "Manifest already targets ${VERSION}; skipping deploy PR."
  exit 0
fi

git add "$MANIFEST"
if [[ "$IS_CURRENT" == "true" || "$FORCE_REDEPLOY" == "true" ]]; then
  git commit -m "deploy(${SERVICE_SLUG}): ${VERSION} (redeploy)"
else
  git commit -m "deploy(${SERVICE_SLUG}): ${VERSION}"
fi
if ! git push -u origin "$BRANCH"; then
  git fetch origin "$BRANCH"
  if git show "origin/$BRANCH:$MANIFEST" | grep -q "${IMAGE_REPO}:${VERSION}"; then
    echo "Remote branch origin/${BRANCH} already targets ${VERSION}; reusing it."
    git checkout -B "$BRANCH" "origin/$BRANCH"
  else
    echo "Push to origin/${BRANCH} rejected and remote manifest does not match ${VERSION}." >&2
    exit 1
  fi
fi

EXISTING="$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || true)"
if [[ -n "$EXISTING" && "$EXISTING" != "null" ]]; then
  echo "Deploy PR already open: #${EXISTING}"
  gh pr view "$EXISTING" --json url --jq .url
  exit 0
fi

if [[ "$IS_CURRENT" == "true" || "$FORCE_REDEPLOY" == "true" ]]; then
  PR_TITLE="deploy(${SERVICE_SLUG}): ${VERSION} (redeploy)"
  PR_NOTE="Пересборка и передеплой версии \`${VERSION}\`."
else
  PR_TITLE="deploy(${SERVICE_SLUG}): ${VERSION}"
  PR_NOTE="После merge Argo CD задеплоит новую версию в кластер."
fi

gh pr create \
  --base main \
  --head "$BRANCH" \
  --title "$PR_TITLE" \
  --body "$(cat <<EOF
Образ \`${IMAGE_REPO}:${VERSION}\` собран и запушен в Docker Hub.

${PR_NOTE}

- Git tag: \`${GIT_TAG}\`
- Manifest: \`${MANIFEST}\`
EOF
)"
