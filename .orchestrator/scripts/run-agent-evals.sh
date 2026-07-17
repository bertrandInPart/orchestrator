#!/usr/bin/env bash
#
# run-agent-evals.sh
#
# For a given agent: runs each case's input through that agent's chatmode (in an isolated
# sandbox - NEVER against a real issue or the live Projects board), captures the output, runs it
# through eval-grader.chatmode.md, and appends a result line to
# .orchestrator/evals/results/<agent>-<date>.json (pass/fail per criterion, per case).
#
# IMPORTANT — be realistic about what this script can automate (blueprint §12.5): chatmodes are
# Copilot agent-mode/cloud-agent prompts, not standalone executables. There is no supported way
# from a plain shell script to invoke "run this chatmode against this input and capture its
# output" without a Copilot session actually running it. This script therefore does NOT attempt
# to invoke the chatmode itself — it is a harness for the parts that ARE mechanical (validating
# eval structure, and recording/aggregating results a human or a Copilot cloud agent task
# produces), and it prints the manual/semi-manual steps for the rest.
#
# Practical invocation (see .orchestrator/evals/README expectations and blueprint §12.5): trigger this as a
# manually-invoked Copilot cloud agent task (or a scheduled automation) whenever a PR touches
# .github/chatmodes/** or .github/instructions/**, with a prompt that:
#   1. For each case file in .orchestrator/evals/<agent>/cases/, runs <agent>.chatmode.md against that case's
#      "Input" section in an isolated sandbox (no real issue/board access).
#   2. Feeds the case's Input, Answer key, .orchestrator/evals/<agent>/rubric.yml, and the agent's actual output
#      to eval-grader.chatmode.md.
#   3. Appends the grader's JSON result object(s) to .orchestrator/evals/results/<agent>-<date>.json using this
#      script's --append-result mode.
#
# Usage:
#   ./.orchestrator/scripts/run-agent-evals.sh --list-cases <agent>
#   ./.orchestrator/scripts/run-agent-evals.sh --append-result <agent> <json-result-file>
#   ./.orchestrator/scripts/run-agent-evals.sh --summarize <agent>

set -euo pipefail

EVALS_DIR=".orchestrator/evals"
RESULTS_DIR="${EVALS_DIR}/results"

usage() {
  echo "Usage:" >&2
  echo "  $0 --list-cases <agent>" >&2
  echo "  $0 --append-result <agent> <json-result-file>" >&2
  echo "  $0 --summarize <agent>" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage

MODE="$1"
shift

case "$MODE" in
  --list-cases)
    AGENT="${1:?agent name required}"
    CASES_DIR="${EVALS_DIR}/${AGENT}/cases"
    if [[ ! -d "$CASES_DIR" ]]; then
      echo "ERROR: no cases directory at ${CASES_DIR}" >&2
      exit 1
    fi
    echo "Cases for '${AGENT}':"
    for f in "${CASES_DIR}"/*.md; do
      [[ -e "$f" ]] || continue
      echo "  - $(basename "$f")"
    done
    ;;

  --append-result)
    AGENT="${1:?agent name required}"
    RESULT_FILE="${2:?json result file required}"
    if [[ ! -f "$RESULT_FILE" ]]; then
      echo "ERROR: result file '${RESULT_FILE}' not found." >&2
      exit 1
    fi
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
    mkdir -p "$RESULTS_DIR"
    DATE_STR=$(date -u +%Y-%m-%d)
    OUT_FILE="${RESULTS_DIR}/${AGENT}-${DATE_STR}.json"
    python3 - "$RESULT_FILE" "$OUT_FILE" <<'PYEOF'
import json
import sys

result_file, out_file = sys.argv[1], sys.argv[2]

with open(result_file) as f:
    new_result = json.load(f)

existing = []
try:
    with open(out_file) as f:
        existing = json.load(f)
        if not isinstance(existing, list):
            existing = [existing]
except FileNotFoundError:
    pass

existing.append(new_result)

with open(out_file, "w") as f:
    json.dump(existing, f, indent=2)
    f.write("\n")

print(f"Appended result to {out_file}")
PYEOF
    ;;

  --summarize)
    AGENT="${1:?agent name required}"
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
    LATEST=$(ls -1 "${RESULTS_DIR}/${AGENT}-"*.json 2>/dev/null | sort | tail -n1 || true)
    if [[ -z "$LATEST" ]]; then
      echo "No results found for '${AGENT}' in ${RESULTS_DIR}." >&2
      exit 1
    fi
    echo "Summarizing ${LATEST}:"
    python3 - "$LATEST" <<'PYEOF'
import json
import sys

with open(sys.argv[1]) as f:
    results = json.load(f)

total = 0
passed = 0
for entry in results:
    for c in entry.get("criteria", []):
        if c["verdict"] == "not_applicable":
            continue
        total += 1
        if c["verdict"] == "pass":
            passed += 1

rate = (passed / total * 100) if total else 0.0
print(f"{passed}/{total} criteria passed ({rate:.1f}%)")
PYEOF
    ;;

  *)
    usage
    ;;
esac
