#!/usr/bin/env bash
#
# update-ticket-stage.sh
#
# Helper used by every agent (see github-workflow.instructions.md) to move a
# feature's ticket on the Projects (v2) board. Wraps the multi-step `gh
# project item-edit` flow (which needs internal item/field/option IDs, not
# human-readable names) behind a single command that takes plain names.
#
# This script is called BY agents during normal operation — unlike
# setup-github-project.sh, which is a one-time human-run setup step.
#
# Usage:
#   ./scripts/update-ticket-stage.sh <issue-number> --field "Stage" --value "Architecture Review"
#   ./scripts/update-ticket-stage.sh <issue-number> --field "Current Agent" --value "architect"
#   ./scripts/update-ticket-stage.sh <issue-number> --field "Feature Slug" --value "user-avatar-upload"
#
# Requires PROJECT_OWNER and PROJECT_NUMBER to be set as environment
# variables, or exported from .github/instructions/github-workflow.instructions.md's
# recorded values before this is called.

set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <issue-number> --field <field-name> --value <value>" >&2
  exit 1
fi

ISSUE_NUMBER="$1"
shift

FIELD_NAME=""
FIELD_VALUE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --field) FIELD_NAME="$2"; shift 2 ;;
    --value) FIELD_VALUE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

: "${PROJECT_OWNER:?PROJECT_OWNER env var must be set (see github-workflow.instructions.md)}"
: "${PROJECT_NUMBER:?PROJECT_NUMBER env var must be set (see github-workflow.instructions.md)}"
: "${FIELD_NAME:?--field is required}"
: "${FIELD_VALUE:?--value is required}"

command -v gh >/dev/null 2>&1 || { echo "ERROR: GitHub CLI (gh) is required." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 1; }

echo "==> Locating project item for issue #${ISSUE_NUMBER}..."
ITEMS_JSON=$(gh project item-list "${PROJECT_NUMBER}" --owner "${PROJECT_OWNER}" --format json)
ITEM_ID=$(echo "${ITEMS_JSON}" | jq -r --arg n "${ISSUE_NUMBER}" \
  '.items[] | select(.content.number == ($n | tonumber)) | .id')

if [[ -z "${ITEM_ID}" ]]; then
  echo "ERROR: no project item found for issue #${ISSUE_NUMBER}. Has it been added to the board?" >&2
  echo "       (add-to-project.yml should have done this automatically on issue creation.)" >&2
  exit 1
fi

echo "==> Locating field '${FIELD_NAME}'..."
FIELDS_JSON=$(gh project field-list "${PROJECT_NUMBER}" --owner "${PROJECT_OWNER}" --format json)
FIELD_ID=$(echo "${FIELDS_JSON}" | jq -r --arg name "${FIELD_NAME}" \
  '.fields[] | select(.name == $name) | .id')

if [[ -z "${FIELD_ID}" ]]; then
  echo "ERROR: no field named '${FIELD_NAME}' found on project #${PROJECT_NUMBER}." >&2
  exit 1
fi

FIELD_TYPE=$(echo "${FIELDS_JSON}" | jq -r --arg name "${FIELD_NAME}" \
  '.fields[] | select(.name == $name) | .type')

if [[ "${FIELD_TYPE}" == "ProjectV2SingleSelectField" ]]; then
  OPTION_ID=$(echo "${FIELDS_JSON}" | jq -r --arg name "${FIELD_NAME}" --arg val "${FIELD_VALUE}" \
    '.fields[] | select(.name == $name) | .options[] | select(.name == $val) | .id')
  if [[ -z "${OPTION_ID}" ]]; then
    echo "ERROR: '${FIELD_VALUE}' is not a valid option for field '${FIELD_NAME}'." >&2
    exit 1
  fi
  echo "==> Setting '${FIELD_NAME}' to '${FIELD_VALUE}' on issue #${ISSUE_NUMBER}..."
  gh project item-edit \
    --id "${ITEM_ID}" \
    --project-id "${PROJECT_NUMBER}" \
    --field-id "${FIELD_ID}" \
    --single-select-option-id "${OPTION_ID}"
else
  echo "==> Setting '${FIELD_NAME}' to '${FIELD_VALUE}' on issue #${ISSUE_NUMBER}..."
  gh project item-edit \
    --id "${ITEM_ID}" \
    --project-id "${PROJECT_NUMBER}" \
    --field-id "${FIELD_ID}" \
    --text "${FIELD_VALUE}"
fi

echo "==> Done."
