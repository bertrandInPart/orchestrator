#!/usr/bin/env python3
"""
check-eval-freshness.py

CI gate that wires .orchestrator/evals/** into the required-checks path (blueprint's eval-loop section, and
.orchestrator/scripts/run-agent-evals.sh's own header comment about the realistic split between what a plain
CI job can and can't automate).

What a GitHub Actions job genuinely CANNOT do: invoke a chatmode and capture its output — that
needs an actual Copilot agent session. So this script does not try to. What it CAN do, and does:

1. Validate the mechanical structure of .orchestrator/evals/** (every rubric criterion's applies_to references
   a case file that exists, and every case file is covered by at least one criterion) — a pure
   fixture-authoring check, always run, always a hard failure if wrong. No excuse to skip this.

2. Determine which chain agents are affected by this diff's changed files (a chatmode, a shared
   skill, a shared instructions file, or an agent's own eval fixtures), and require that the SAME
   diff also adds/updates a graded results file under .orchestrator/evals/results/<agent>-*.json for every
   affected agent. This is the actual regression gate: it does not verify the *content* of that
   result (a human or the eval-grader chatmode already did that when producing the file) — it
   verifies that grading evidence was not skipped when the thing being graded changed.

Usage:
  python .orchestrator/scripts/check-eval-freshness.py <base-ref> <head-ref>

Exit code 0 = pass, 1 = fail (either a structural error or missing eval evidence).
"""
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVALS_DIR = REPO_ROOT / ".orchestrator" / "evals"

ALL_AGENTS = [
    "spec-writer",
    "architect",
    "backend-builder",
    "frontend-builder",
    "test-engineer",
    "reviewer",
    "release-engineer",
]

# Files/dirs whose change requires fresh eval evidence, and for which agent(s). A single agent's
# own chatmode file is matched inline in affected_agents() below (no per-agent entry needed here).
SHARED_RULES = {
    # Shared skills and cross-cutting instructions govern every agent's behavior.
    ".orchestrator/skills/": ALL_AGENTS,
    ".github/instructions/dor-dod-definitions.md": ALL_AGENTS,
    ".github/instructions/github-workflow.instructions.md": ALL_AGENTS,
    ".github/instructions/security.instructions.md": ALL_AGENTS,
    ".github/chatmodes/eval-grader.chatmode.md": ALL_AGENTS,
    # Stack-scoped instructions only govern the agent(s) that write in that stack.
    ".github/instructions/backend.instructions.md": ["backend-builder"],
    ".github/instructions/data.instructions.md": ["backend-builder"],
    ".github/instructions/frontend.instructions.md": ["frontend-builder"],
    ".github/instructions/testing.instructions.md": ["test-engineer"],
}


def sh(*args):
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def changed_files(base_ref, head_ref):
    out = sh("git", "diff", "--name-status", f"{base_ref}...{head_ref}")
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        files.append((status, path.replace("\\", "/")))
    return files


def validate_eval_structure():
    """Pure fixture-authoring check: every rubric criterion's applies_to matches a real case
    file, and every case file is referenced by at least one criterion. Independent of the diff —
    always run, so a stale/broken fixture can't sit unnoticed until someone happens to touch it."""
    errors = []
    if not EVALS_DIR.is_dir():
        return errors

    for agent_dir in sorted(p for p in EVALS_DIR.iterdir() if p.is_dir() and p.name != "results"):
        agent = agent_dir.name
        rubric_path = agent_dir / "rubric.yml"
        cases_dir = agent_dir / "cases"

        case_ids = set()
        if cases_dir.is_dir():
            for case_file in sorted(cases_dir.glob("*.md")):
                m = re.match(r"^(\d+)-", case_file.name)
                if not m:
                    errors.append(
                        f"{agent}: case file '{case_file.name}' doesn't start with a numeric "
                        f"'NNN-' id prefix — rubric applies_to entries can't reference it."
                    )
                    continue
                case_ids.add(m.group(1))

        if not rubric_path.is_file():
            errors.append(f"{agent}: missing rubric.yml")
            continue

        with rubric_path.open() as f:
            rubric = yaml.safe_load(f) or {}

        criteria = rubric.get("criteria", [])
        referenced_ids = set()
        for c in criteria:
            cid = c.get("id", "<unnamed>")
            for case_id in c.get("applies_to", []):
                referenced_ids.add(case_id)
                if case_id not in case_ids:
                    errors.append(
                        f"{agent}: rubric criterion '{cid}' applies_to unknown case id "
                        f"'{case_id}' (no case file .orchestrator/evals/{agent}/cases/{case_id}-*.md)"
                    )

        for case_id in sorted(case_ids - referenced_ids):
            errors.append(
                f"{agent}: case '{case_id}' is not referenced by any rubric criterion's "
                f"applies_to — it will never actually be graded on anything."
            )

    return errors


def affected_agents(files):
    affected = {}  # agent -> list of triggering paths
    for status, path in files:
        if status == "D":
            continue  # a deletion doesn't need fresh evidence that it still passes
        if path.startswith(".github/chatmodes/") and path.endswith(".chatmode.md"):
            agent_name = path[len(".github/chatmodes/"):-len(".chatmode.md")]
            if agent_name in ALL_AGENTS:
                affected.setdefault(agent_name, []).append(path)
                continue
        for rule_prefix, agents in SHARED_RULES.items():
            if path == rule_prefix or path.startswith(rule_prefix):
                for a in agents:
                    affected.setdefault(a, []).append(path)
        m = re.match(r"^\.orchestrator/evals/([\w-]+)/(rubric\.yml|cases/.+\.md)$", path)
        if m and m.group(1) in ALL_AGENTS:
            affected.setdefault(m.group(1), []).append(path)
    return affected


def has_fresh_result(agent, files):
    pattern = re.compile(rf"^\.orchestrator/evals/results/{re.escape(agent)}-.*\.json$")
    return any(status in ("A", "M") and pattern.match(path) for status, path in files)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <base-ref> <head-ref>", file=sys.stderr)
        sys.exit(2)
    base_ref, head_ref = sys.argv[1], sys.argv[2]

    struct_errors = validate_eval_structure()
    if struct_errors:
        print("FAIL: .orchestrator/evals/** structural problems (fix these regardless of what triggered this run):")
        for e in struct_errors:
            print(f"  - {e}")
        sys.exit(1)
    print("OK: .orchestrator/evals/** fixture structure is internally consistent.")

    files = changed_files(base_ref, head_ref)
    affected = affected_agents(files)

    if not affected:
        print("OK: no chatmode/skill/instructions/eval-fixture changes in this diff — nothing requires fresh eval evidence.")
        sys.exit(0)

    missing = []
    for agent, triggers in sorted(affected.items()):
        if has_fresh_result(agent, files):
            print(f"OK: '{agent}' affected by {triggers[:3]}{'...' if len(triggers) > 3 else ''}, and this diff includes a fresh .orchestrator/evals/results/{agent}-*.json.")
        else:
            missing.append((agent, triggers))

    if missing:
        print("\nFAIL: the following agents are affected by this diff but have no fresh graded")
        print("results included in it. A chatmode/skill/instructions change must be accompanied")
        print("by evidence it was actually run through .orchestrator/evals/<agent>/cases/ and graded — that's")
        print("the whole point of this gate (blueprint's eval-loop section).")
        print("\nTo fix: start an interactive Copilot session, adopt the eval-grader chatmode for")
        print("each case in .orchestrator/evals/<agent>/cases/ against the target chatmode's actual output, then")
        print("run:  ./.orchestrator/scripts/run-agent-evals.sh --append-result <agent> <graded-result.json>")
        print("and commit the resulting .orchestrator/evals/results/<agent>-<date>.json in this same PR.\n")
        for agent, triggers in missing:
            print(f"  - {agent}: triggered by {triggers[:5]}{'...' if len(triggers) > 5 else ''}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
