#!/usr/bin/env bash
#
# log-agent-run.sh
#
# Appends one validated JSON line to docs/ops/agent-telemetry.jsonl,
# committed as part of the agent's own stage commit so it travels with the
# rest of that stage's changes. This is what §10's circuit breaker and the
# eval loop's regression tracking both read from.
#
# Usage:
#   ./scripts/log-agent-run.sh \
#     --feature-slug "user-avatar-upload" \
#     --issue-number 42 \
#     --agent "backend-builder" \
#     --stage "Implementation" \
#     --started-at "2026-07-09T10:03:00Z" \
#     --outcome "success" \
#     --attempt 1

set -euo pipefail

LOG_FILE="docs/ops/agent-telemetry.jsonl"

FEATURE_SLUG=""
ISSUE_NUMBER=""
AGENT=""
STAGE=""
STARTED_AT=""
OUTCOME=""
ATTEMPT="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-slug) FEATURE_SLUG="$2"; shift 2 ;;
    --issue-number) ISSUE_NUMBER="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    --started-at) STARTED_AT="$2"; shift 2 ;;
    --outcome) OUTCOME="$2"; shift 2 ;;
    --attempt) ATTEMPT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

: "${FEATURE_SLUG:?--feature-slug is required}"
: "${ISSUE_NUMBER:?--issue-number is required}"
: "${AGENT:?--agent is required}"
: "${STAGE:?--stage is required}"
: "${STARTED_AT:?--started-at is required (ISO 8601, e.g. 2026-07-09T10:03:00Z)}"
: "${OUTCOME:?--outcome is required (success|fail|timeout)}"

if [[ "${OUTCOME}" != "success" && "${OUTCOME}" != "fail" && "${OUTCOME}" != "timeout" ]]; then
  echo "ERROR: --outcome must be one of: success, fail, timeout" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
mkdir -p "$(dirname "${LOG_FILE}")"

python3 - "$LOG_FILE" "$FEATURE_SLUG" "$ISSUE_NUMBER" "$AGENT" "$STAGE" "$STARTED_AT" "$OUTCOME" "$ATTEMPT" <<'PYEOF'
import json
import sys
from datetime import datetime, timezone

(log_file, feature_slug, issue_number, agent, stage,
 started_at, outcome, attempt) = sys.argv[1:9]

finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

try:
    started_dt = datetime.strptime(started_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    finished_dt = datetime.strptime(finished_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    duration_seconds = int((finished_dt - started_dt).total_seconds())
except ValueError:
    print(f"ERROR: --started-at must match format YYYY-MM-DDTHH:MM:SSZ, got '{started_at}'", file=sys.stderr)
    sys.exit(1)

entry = {
    "feature_slug": feature_slug,
    "issue_number": int(issue_number),
    "agent": agent,
    "stage": stage,
    "started_at": started_at,
    "finished_at": finished_at,
    "duration_seconds": duration_seconds,
    "outcome": outcome,
    "attempt_number": int(attempt),
}

with open(log_file, "a") as f:
    f.write(json.dumps(entry) + "\n")

print(f"Logged: {agent} / {stage} / {outcome} (attempt {attempt}, {duration_seconds}s) for issue #{issue_number}")
PYEOF
