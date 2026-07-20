#!/usr/bin/env bash
#
# check-agent-boundaries.sh
#
# Required CI check (wired into ci.yml) run on every push to a feature/**
# branch and on every PR. For each commit in range:
#   1. Reads the `Agent: <name>` trailer from the commit message. Missing or
#      unrecognized -> fail immediately, no silent skip.
#   2. For each file changed in that commit, checks it against that agent's
#      allow-list in .orchestrator/agent-boundaries.yml, and separately against
#      the `never` list.
#   3. Fails the build, printing the offending commit SHA, agent, and file,
#      on any violation.
#
# Usage:
#   ./.orchestrator/scripts/check-agent-boundaries.sh <base-ref> <head-ref>
#
# Example (as used in ci.yml against a PR):
#   ./.orchestrator/scripts/check-agent-boundaries.sh origin/main HEAD

set -euo pipefail

BOUNDARIES_FILE=".orchestrator/agent-boundaries.yml"
CONFIG_FILE=".orchestrator/config.yml"

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
python3 - "$BOUNDARIES_FILE" "$CONFIG_FILE" "$BASE_REF" "$HEAD_REF" <<'PYEOF'
import subprocess
import sys
import re
import fnmatch

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml --break-system-packages).", file=sys.stderr)
    sys.exit(1)

boundaries_file, config_file, base_ref, head_ref = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

# agent-boundaries.yml ships generic/unmodified from the orchestrator template
# (or submodule) and uses `{{backend.path}}` / `{{frontend.path}}` /
# `{{migrations.path}}` placeholders instead of baking this project's literal
# directory layout into a file that would otherwise need per-project edits.
# Resolve those placeholders against this project's own config.yml before
# parsing the boundaries as YAML, so one generic boundaries file works for
# any consuming repo.
UNRESOLVED = "__unresolved__"
NOT_APPLICABLE_VALUES = {"", "n/a", "na", "none", "null"}


def normalize_configured_path(value: str, enabled: bool = True) -> str:
    """Turn a config.yml path value into something safe to splice into a glob.

    - A disabled side of the stack (or an empty/"N/A"-style placeholder value,
      e.g. a repo with no migrations) must never resolve to a pattern that
      matches real files, so it maps to a sentinel directory name instead.
    - "." (this side of the stack *is* the repo root, e.g. a backend-only repo)
      must resolve to "" so "{{backend.path}}/**" becomes "**", not "./**"
      (which — see matches_any below — would otherwise never match anything).
    """
    value = (value or "").strip()
    if not enabled or value.lower() in NOT_APPLICABLE_VALUES:
        return UNRESOLVED
    if value in (".", "./"):
        return ""
    return value.rstrip("/")


def load_path_placeholders(path: str) -> dict[str, str]:
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"WARNING: {path} not found — leaving path placeholders unresolved.", file=sys.stderr)
        return {}
    backend_cfg = cfg.get("backend") or {}
    frontend_cfg = cfg.get("frontend") or {}
    database_cfg = cfg.get("database") or {}
    return {
        "{{backend.path}}": normalize_configured_path(
            backend_cfg.get("path", ""), backend_cfg.get("enabled", True)
        ),
        "{{frontend.path}}": normalize_configured_path(
            frontend_cfg.get("path", ""), frontend_cfg.get("enabled", True)
        ),
        "{{migrations.path}}": normalize_configured_path(database_cfg.get("migrations_path", "")),
    }

placeholders = load_path_placeholders(config_file)

with open(boundaries_file) as f:
    boundaries_text = f.read()

for token, value in placeholders.items():
    # Every occurrence in agent-boundaries.yml is written as "{{token}}/..."
    # (the placeholder is always the directory itself, never a bare file). If
    # the resolved value is empty (this side of the stack lives at the repo
    # root, config path "."), collapse "{{token}}/" to "" too, so e.g.
    # "{{backend.path}}/**" becomes "**" instead of the unmatchable "/**".
    boundaries_text = boundaries_text.replace(f"{token}/", f"{value}/" if value else "")
    boundaries_text = boundaries_text.replace(token, value)

# Any placeholder left over means config.yml is missing that key (or the
# corresponding side of the stack is disabled/unset) — collapse it to a
# pattern that can never match a real path, rather than letting a literal
# "{{...}}" string leak into a glob comparison.
boundaries_text = re.sub(r"\{\{[a-z.]+\}\}", "__unresolved__", boundaries_text)

boundaries = yaml.safe_load(boundaries_text)

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
