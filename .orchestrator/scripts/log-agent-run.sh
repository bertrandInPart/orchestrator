#!/usr/bin/env bash
#
# log-agent-run.sh
#
# Appends one validated JSON line to .orchestrator/docs/ops/agent-telemetry.jsonl,
# committed as part of the agent's own stage commit so it travels with the
# rest of that stage's changes. This is what §10's circuit breaker and the
# eval loop's regression tracking both read from.
#
# --outcome must be one of:
#   success      - DoD passed, stage handed off normally
#   fail         - a DoR/DoD criterion genuinely wasn't met (a quality problem)
#   timeout      - a previous attempt hung past its stage timeout (see
#                  on-start-checks.skill.md's "stage-timeout label" handling)
#   infra_error  - a transient, non-quality failure (rate limit, network blip, a
#                  tool temporarily unavailable). Logged for visibility only -
#                  see the note below on why this doesn't feed the circuit breaker.
#
# Usage:
#   ./.orchestrator/scripts/log-agent-run.sh \
#     --feature-slug "user-avatar-upload" \
#     --issue-number 42 \
#     --agent "backend-builder" \
#     --stage "Implementation" \
#     --started-at "2026-07-09T10:03:00Z" \
#     --outcome "success" \
#     --attempt 1 \
#     --tokens-input 18234 \
#     --tokens-output 4021
#
# --tokens-input / --tokens-output are optional and best-effort: include them only if your own
# runtime actually exposes your session's token usage to you. Most agent runs won't have a
# reliable way to know this from inside the run itself - that's fine, omit them rather than
# guessing. Never estimate or fabricate a number here; an absent field is more honest than a wrong
# one, and telemetry-rollup.py treats missing values as "not reported," not zero.

set -euo pipefail

LOG_FILE=".orchestrator/docs/ops/agent-telemetry.jsonl"

FEATURE_SLUG=""
ISSUE_NUMBER=""
AGENT=""
STAGE=""
STARTED_AT=""
OUTCOME=""
ATTEMPT="1"
TOKENS_INPUT=""
TOKENS_OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature-slug) FEATURE_SLUG="$2"; shift 2 ;;
    --issue-number) ISSUE_NUMBER="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    --started-at) STARTED_AT="$2"; shift 2 ;;
    --outcome) OUTCOME="$2"; shift 2 ;;
    --attempt) ATTEMPT="$2"; shift 2 ;;
    --tokens-input) TOKENS_INPUT="$2"; shift 2 ;;
    --tokens-output) TOKENS_OUTPUT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

: "${FEATURE_SLUG:?--feature-slug is required}"
: "${ISSUE_NUMBER:?--issue-number is required}"
: "${AGENT:?--agent is required}"
: "${STAGE:?--stage is required}"
: "${STARTED_AT:?--started-at is required (ISO 8601, e.g. 2026-07-09T10:03:00Z)}"
: "${OUTCOME:?--outcome is required (success|fail|timeout|infra_error)}"

if [[ "${OUTCOME}" != "success" && "${OUTCOME}" != "fail" && "${OUTCOME}" != "timeout" && "${OUTCOME}" != "infra_error" ]]; then
  echo "ERROR: --outcome must be one of: success, fail, timeout, infra_error" >&2
  exit 1
fi
# infra_error is for transient, non-quality failures (rate limits, API blips, a tool being
# temporarily unavailable) - it is logged for visibility but deliberately does NOT count toward
# the circuit breaker in on-start-checks.skill.md, which only counts fail/timeout. This keeps a
# GitHub API hiccup from burning one of the 3 retry slots meant for real quality problems.

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
mkdir -p "$(dirname "${LOG_FILE}")"

python3 - "$LOG_FILE" "$FEATURE_SLUG" "$ISSUE_NUMBER" "$AGENT" "$STAGE" "$STARTED_AT" "$OUTCOME" "$ATTEMPT" "$TOKENS_INPUT" "$TOKENS_OUTPUT" <<'PYEOF'
import json
import sys
from datetime import datetime, timezone

(log_file, feature_slug, issue_number, agent, stage,
 started_at, outcome, attempt, tokens_input, tokens_output) = sys.argv[1:11]

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

# Optional, best-effort - omitted entirely (not set to 0/null) when not provided, so the rollup
# can tell "not reported" apart from "reported as zero."
for field_name, raw_value in (("tokens_input", tokens_input), ("tokens_output", tokens_output)):
    if raw_value == "":
        continue
    try:
        entry[field_name] = int(raw_value)
    except ValueError:
        print(f"ERROR: --{field_name.replace('_', '-')} must be an integer, got '{raw_value}'", file=sys.stderr)
        sys.exit(1)

with open(log_file, "a") as f:
    f.write(json.dumps(entry) + "\n")

token_note = ""
if "tokens_input" in entry or "tokens_output" in entry:
    token_note = f", tokens in={entry.get('tokens_input', 'n/a')}/out={entry.get('tokens_output', 'n/a')}"
print(f"Logged: {agent} / {stage} / {outcome} (attempt {attempt}, {duration_seconds}s{token_note}) for issue #{issue_number}")
PYEOF
