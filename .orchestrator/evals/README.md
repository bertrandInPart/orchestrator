# .orchestrator/evals/ — regression harness for the chain's own chatmodes

This directory does **not** test the app being built by the chain — it tests the chain's agents
themselves: does `architect.chatmode.md` still produce an architecture that satisfies its rubric
after someone edits it? Did a "small wording tweak" to a shared skill quietly change the Reviewer's
behavior on the PII case? That's what `.orchestrator/evals/` and the `eval-gate` CI job exist to catch, per the
Agentic SDLC Handbook's eval-loop guidance.

## Layout

```
.orchestrator/evals/
  <agent>/
    rubric.yml       # every criterion this agent's output is judged on, tagged with which
                      # case id(s) it applies to
    cases/
      001-*.md        # a fixed input + an answer key (properties a good output must have -
      002-*.md        # not a golden output to diff against)
  results/
    <agent>-<date>.json  # graded verdicts produced by eval-grader.chatmode.md, one array entry
                          # per case graded, each with a pass/fail/not_applicable per criterion
```

## What CI actually enforces (`eval-gate` job in `.github/workflows/ci.yml`)

A GitHub Actions job cannot invoke a chatmode and read its output — that requires a real Copilot
agent session, not a shell script. So `.orchestrator/scripts/check-eval-freshness.py` enforces the two things
that genuinely are mechanical:

1. **Fixture structure is self-consistent.** Every rubric criterion's `applies_to` points at a
   case file that actually exists, and every case file is covered by at least one criterion.
   Always checked, regardless of what the PR touches — a broken fixture is a bug the moment it's
   introduced, not just when someone happens to touch that agent next.
2. **Changes to a chatmode, a shared skill/instructions file, or an agent's own eval fixtures must
   ship with fresh graded evidence in the same PR.** The script maps changed paths to the agent(s)
   they govern (a single agent's own `.chatmode.md`; `.orchestrator/skills/**` and the cross-cutting
   instructions files affect all seven chain agents; stack-scoped instructions
   like `backend.instructions.md` affect just that stack's agent; an agent's own
   `.orchestrator/evals/<agent>/**` affects that agent) and fails the build if any affected agent has no
   added/updated `.orchestrator/evals/results/<agent>-*.json` in the diff.

This is a **required-evidence gate, not an auto-runner**. It cannot verify the graded verdicts are
*correct* — that's still on whoever produced them (a human, or the eval-grader chatmode) — it only
verifies grading wasn't skipped when the thing being graded changed.

## How to actually run an eval pass (produce the evidence CI wants)

There's no standalone executable that runs a chatmode; do this from an interactive Copilot
session (see `.orchestrator/scripts/run-agent-evals.sh`'s header comment for the full rationale):

1. `./.orchestrator/scripts/run-agent-evals.sh --list-cases <agent>` to see which cases exist.
2. For each case, adopt `<agent>.chatmode.md` in an isolated sandbox (never a real issue or the
   live Projects board) and run it against that case's `Input` section.
3. Adopt `eval-grader.chatmode.md` and give it: the case's `Input`, its `Answer key`,
   `.orchestrator/evals/<agent>/rubric.yml`, and the output from step 2. It returns one JSON result object per
   case per the format in its own chatmode file.
4. `./.orchestrator/scripts/run-agent-evals.sh --append-result <agent> <result.json>` to fold it into
   `.orchestrator/evals/results/<agent>-<date>.json`.
5. `./.orchestrator/scripts/run-agent-evals.sh --summarize <agent>` for a quick pass-rate readout.
6. Commit the updated `.orchestrator/evals/results/<agent>-<date>.json` in the same PR as the chatmode/skill
   change that prompted the run.

## Automation 8 — periodic eval sweep

A scheduled Copilot cloud agent workflow (`eval-sweep`, weekly, see `.orchestrator/automations/README.md`)
runs this same loop across all seven agents against the current `develop` branch and commits any
resulting `.orchestrator/evals/results/**` updates directly, independent of any specific PR. This exists to catch
drift that isn't tied to an obvious diff (e.g. a shared skill edited months ago whose effect on one
agent's case only shows up after an unrelated model update) — the PR-level gate above only reacts
to changes visible in that PR's own diff.
