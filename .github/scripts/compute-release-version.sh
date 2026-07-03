#!/usr/bin/env bash
# Computes release semver from git tags.
# Usage: compute-release-version.sh <tag-prefix> <major|minor|patch|current> [docker-image-repo]
# Example: compute-release-version.sh llm-orchestrator-api/v patch deniskocs/llm-orchestrator-api
set -euo pipefail

TAG_PREFIX="${1:?tag prefix required (e.g. llm-orchestrator-api/v)}"
BUMP="${2:?bump required (major, minor, patch, or current)}"
DOCKER_IMAGE_REPO="${3:-}"

case "$BUMP" in
  major | minor | patch | current) ;;
  *)
    echo "Invalid bump: $BUMP (expected major, minor, patch, or current)" >&2
    exit 1
    ;;
esac

LATEST="$(git tag -l "${TAG_PREFIX}*" | sort -V | tail -n1 || true)"

if [[ "$BUMP" == "current" ]]; then
  if [[ -z "$LATEST" ]]; then
    echo "No release tags found for prefix ${TAG_PREFIX}; cannot redeploy current." >&2
    exit 1
  fi
  VERSION="${LATEST#"${TAG_PREFIX}"}"
  if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Latest tag has unsupported semver: $LATEST" >&2
    exit 1
  fi
  GIT_TAG="$LATEST"
  TAG_MODE="retag"
  echo "Redeploy current version: $VERSION (latest tag: $LATEST)"
else
  if [[ -z "$LATEST" ]]; then
    MAJOR=0
    MINOR=0
    PATCH=0
  else
    VERSION="${LATEST#"${TAG_PREFIX}"}"
    if [[ ! "$VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
      echo "Latest tag has unsupported semver: $LATEST" >&2
      exit 1
    fi
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
  fi

  case "$BUMP" in
    major)
      MAJOR=$((MAJOR + 1))
      MINOR=0
      PATCH=0
      ;;
    minor)
      MINOR=$((MINOR + 1))
      PATCH=0
      ;;
    patch)
      PATCH=$((PATCH + 1))
      ;;
  esac

  VERSION="${MAJOR}.${MINOR}.${PATCH}"
  GIT_TAG="${TAG_PREFIX}${VERSION}"
  TAG_MODE="new"
  echo "Computed release version: $VERSION (from bump: $BUMP, latest tag: ${LATEST:-none})"
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "version=$VERSION"
    echo "git_tag=$GIT_TAG"
    echo "tag_mode=$TAG_MODE"
  } >>"$GITHUB_OUTPUT"
  if [[ -n "$DOCKER_IMAGE_REPO" ]]; then
    echo "docker_tag=${DOCKER_IMAGE_REPO}:${VERSION}" >>"$GITHUB_OUTPUT"
  fi
fi
