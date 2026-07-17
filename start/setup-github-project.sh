#!/usr/bin/env bash
#
# setup-github-project.sh
#
# ONE-TIME setup script. Run this once, by a human, before the first feature
# enters the chain. It creates the GitHub Projects (v2) board and the three
# custom fields the agent chain depends on: Stage, Feature Slug, Current Agent.
#
# It does NOT run per-feature and it is not invoked by any agent — agents only
# read/write the fields this script creates (see scripts/update-ticket-stage.sh
# and .github/instructions/github-workflow.instructions.md for that).
#
# Requirements:
#   - GitHub CLI (`gh`) installed and authenticated: gh auth login
#   - `jq` installed (used to parse `gh`'s JSON output)
#   - You must have permission to create projects for the given owner
#
# Usage:
#   ./scripts/setup-github-project.sh <owner> <repo> ["<project title>"]
#
# Example:
#   ./scripts/setup-github-project.sh my-org my-web-app "Feature Chain"

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <owner> <repo> [\"<project title>\"]" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
TITLE="${3:-Agentic Feature Chain}"

command -v gh >/dev/null 2>&1 || { echo "ERROR: GitHub CLI (gh) is required." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 1; }

echo "==> Creating Projects (v2) board '${TITLE}' for owner '${OWNER}'..."
CREATE_JSON=$(gh project create --owner "${OWNER}" --title "${TITLE}" --format json)
PROJECT_NUMBER=$(echo "${CREATE_JSON}" | jq -r '.number')
PROJECT_URL=$(echo "${CREATE_JSON}" | jq -r '.url')

if [[ -z "${PROJECT_NUMBER}" || "${PROJECT_NUMBER}" == "null" ]]; then
  echo "ERROR: could not determine project number from gh output:" >&2
  echo "${CREATE_JSON}" >&2
  exit 1
fi

echo "==> Created project #${PROJECT_NUMBER} — ${PROJECT_URL}"

echo "==> Creating 'Stage' single-select field..."
gh project field-create "${PROJECT_NUMBER}" \
  --owner "${OWNER}" \
  --name "Stage" \
  --data-type "SINGLE_SELECT" \
  --single-select-options "Backlog,Spec Drafting,Spec Review,Architecture Drafting,Architecture Review,Implementation,Testing,Governance Review,Release Prep,PR Open,Done"

echo "==> Creating 'Feature Slug' text field..."
gh project field-create "${PROJECT_NUMBER}" \
  --owner "${OWNER}" \
  --name "Feature Slug" \
  --data-type "TEXT"

echo "==> Creating 'Current Agent' single-select field..."
gh project field-create "${PROJECT_NUMBER}" \
  --owner "${OWNER}" \
  --name "Current Agent" \
  --data-type "SINGLE_SELECT" \
  --single-select-options "spec-writer,architect,backend-builder,frontend-builder,test-engineer,reviewer,release-engineer,none"

echo "==> Creating 'Feature Branch' text field..."
gh project field-create "${PROJECT_NUMBER}" \
  --owner "${OWNER}" \
  --name "Feature Branch" \
  --data-type "TEXT"

echo "==> Linking repository '${OWNER}/${REPO}' to the project..."
gh project link "${PROJECT_NUMBER}" --owner "${OWNER}" --repo "${OWNER}/${REPO}" || \
  echo "    (Non-fatal: link the repo manually in the project settings UI if this failed.)"

cat <<EOF

==============================================================================
Setup complete.

  Project number : ${PROJECT_NUMBER}
  Project URL    : ${PROJECT_URL}

Next step (required): record this project number in
.github/instructions/github-workflow.instructions.md, replacing the
<PROJECT_NUMBER> placeholder near the top of that file, so every agent
knows which board to read and write.

Fields created: Stage, Feature Slug, Current Agent, Feature Branch.
==============================================================================
EOF
