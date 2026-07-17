#!/usr/bin/env bash
#
# check-agent-boundaries.sh
#
# Required CI check (wired into ci.yml) run on every push to a feature/**
# branch and on every PR. For each commit in range:
#   1. Reads the `Agent: <name>` trailer from the commit message. Missing or
#      unrecognized -> fail immediately, no silent skip.
#   2. For each file changed in that commit, checks it against that agent's
#      allow-list in .github/agent-boundaries.yml, and separately against
#      the `never` list.
#   3. Fails the build, printing the offending commit SHA, agent, and file,
#      on any violation.
#
# Usage:
#   ./scripts/check-agent-boundaries.sh <base-ref> <head-ref>
#
# Example (as used in ci.yml against a PR):
#   ./scripts/check-agent-boundaries.sh origin/main HEAD

set -euo pipefail

BOUNDARIES_FILE=".github/agent-boundaries.yml"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <base-ref> <head-ref>" >&2
  exit 1
fi

BASE_REF="$1"
HEAD_REF="$2"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is required." >&2; exit 1; }

if [[ ! -f "${BOUNDARIES_FILE}" ]]; then
  echo "ERROR: ${BOUNDARIES_FILE} not found." >&2
  exit 1
fi

# python3 is used for YAML parsing + glob matching (fnmatch handles ** better
# than bash's built-in globbing does for matching against arbitrary strings).
python3 - "$BOUNDARIES_FILE" "$BASE_REF" "$HEAD_REF" <<'PYEOF'
import subprocess
import sys
import re
import fnmatch

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml --break-system-packages).", file=sys.stderr)
    sys.exit(1)

boundaries_file, base_ref, head_ref = sys.argv[1], sys.argv[2], sys.argv[3]

with open(boundaries_file) as f:
    boundaries = yaml.safe_load(f)

never_list = boundaries.pop("never", [])

def matches_any(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        # Translate a leading-** or trailing-** glob into something fnmatch
        # can evaluate against a full relative path, including across
        # directory separators.
        normalized = pattern.replace("**", "*")
        if fnmatch.fnmatch(path, normalized) or fnmatch.fnmatch(path, pattern):
            return True
        # Directory-prefix style patterns like "server/**" should also match
        # "server/" itself and any depth beneath it.
        prefix = pattern.split("**")[0].rstrip("/")
        if prefix and path.startswith(prefix + "/"):
            return True
    return False

commit_range = f"{base_ref}..{head_ref}"
commits = subprocess.run(
    ["git", "log", "--format=%H", commit_range],
    capture_output=True, text=True, check=True
).stdout.strip().splitlines()

if not commits:
    print("No commits in range — nothing to check.")
    sys.exit(0)

failures = []

for sha in commits:
    message = subprocess.run(
        ["git", "log", "-1", "--format=%B", sha],
        capture_output=True, text=True, check=True
    ).stdout

    trailer_match = re.search(r"^Agent:\s*(\S+)\s*$", message, re.MULTILINE)
    if not trailer_match:
        failures.append(f"{sha}: missing required 'Agent:' trailer in commit message.")
        continue

    agent = trailer_match.group(1)
    if agent not in boundaries:
        failures.append(f"{sha}: unrecognized agent name '{agent}' in Agent trailer.")
        continue

    allowed_patterns = boundaries[agent]

    changed_files = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        capture_output=True, text=True, check=True
    ).stdout.strip().splitlines()

    for path in changed_files:
        if matches_any(path, never_list):
            failures.append(f"{sha} ({agent}): '{path}' is in the 'never' list — no agent may touch this path.")
        elif not matches_any(path, allowed_patterns):
            failures.append(f"{sha} ({agent}): '{path}' is outside {agent}'s allowed paths {allowed_patterns}.")

if failures:
    print("Agent boundary violations found:\n", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print(f"OK — checked {len(commits)} commit(s), no boundary violations.")
PYEOF
