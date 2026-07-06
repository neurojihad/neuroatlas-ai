#!/usr/bin/env bash
# Register a project GitLab Runner with docker executor and tag neuroatlas-self-hosted.
#
# Usage:
#   export GITLAB_RUNNER_TOKEN="glrt-..."
#   export GITLAB_PROJECT_URL="https://gitlab.com/neurojihad/neuroatlas"  # optional
#   ./scripts/ci/register-gitlab-runner.sh
#
# Requires: gitlab-runner binary, Docker daemon running.

set -euo pipefail

GITLAB_URL="${GITLAB_URL:-https://gitlab.com/}"
GITLAB_PROJECT_URL="${GITLAB_PROJECT_URL:-https://gitlab.com/neurojihad/neuroatlas}"
RUNNER_TAG="${RUNNER_TAG:-neuroatlas-self-hosted}"
RUNNER_NAME="${RUNNER_NAME:-neuroatlas-self-hosted}"
DEFAULT_IMAGE="${DEFAULT_IMAGE:-python:3.12-slim-bookworm}"

if [[ -z "${GITLAB_RUNNER_TOKEN:-}" ]]; then
  echo "Set GITLAB_RUNNER_TOKEN (from GitLab → Settings → CI/CD → Runners → New project runner)." >&2
  exit 1
fi

if ! command -v gitlab-runner >/dev/null 2>&1; then
  echo "gitlab-runner not found. Install: https://docs.gitlab.com/runner/install/" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not reachable. Start Docker and ensure your user can run docker." >&2
  exit 1
fi

echo "Registering runner '${RUNNER_NAME}' (tags/lock set in GitLab UI when creating the runner)"

sudo gitlab-runner register \
  --non-interactive \
  --url "${GITLAB_URL}" \
  --token "${GITLAB_RUNNER_TOKEN}" \
  --executor "docker" \
  --docker-image "${DEFAULT_IMAGE}" \
  --description "${RUNNER_NAME}"

echo "Done. Verify with: sudo gitlab-runner verify && sudo gitlab-runner list"
