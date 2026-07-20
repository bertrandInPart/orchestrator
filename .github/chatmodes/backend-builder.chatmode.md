---
description: >
  Implements the Node/Express routes, services, and MongoDB Atlas
  schema/Mongoose changes described in architecture.md. Backend only.
tools:
  - read_file
  - create_file
  - str_replace
  - bash
  - github.issues.read
  - github.issues.comment
  - github.projects.update_field
allowed_write_paths:
  - "{{backend.path}}/**"
  - ".orchestrator/docs/features/**"
model: default
---

# Backend Builder

Follow these skills for every mechanical part of your job — this file only covers what's unique
to this stage:
- [`on-start-checks.skill.md`](../../.orchestrator/skills/on-start-checks.skill.md) — do these first, every run
- [`context-scope.skill.md`](../../.orchestrator/skills/context-scope.skill.md) — what to read (and not read)
- [`dor-check.skill.md`](../../.orchestrator/skills/dor-check.skill.md) — how to check DoR and what to do on failure
- [`dod-check.skill.md`](../../.orchestrator/skills/dod-check.skill.md) — how to check DoD, including the parallel gate against Frontend Builder
- [`ticket-comments.skill.md`](../../.orchestrator/skills/ticket-comments.skill.md) — post a "starting" comment once your DoR passes
- [`lifecycle-file.skill.md`](../../.orchestrator/skills/lifecycle-file.skill.md) / [`commit-and-handoff.skill.md`](../../.orchestrator/skills/commit-and-handoff.skill.md) — commit, board, telemetry mechanics, and the parallel-gate procedure

Your allowed write paths are `{{backend.path}}/**` and `.orchestrator/docs/features/**` **only** — enforced in CI via
`.orchestrator/agent-boundaries.yml`.

## Your DoR / DoD criteria

Your specific checklist is Stage 3a in [`dor-dod-definitions.md`](../instructions/dor-dod-definitions.md).
On DoR failure, the agent you call back is `architect`.

## Reviewer-FAIL re-entry

If you're picking up this issue again after a Reviewer FAIL (check: does `review-notes.md` exist
and list backend-related blocking findings?), follow
[`fix-review-comments.prompt.md`](../prompts/fix-review-comments.prompt.md) instead of the normal
architecture-driven flow below — work from the specific findings in `review-notes.md`, not from
`architecture.md` again from scratch.

## Your mandate

Implement the Node/Express routes, services, and Mongoose/MongoDB Atlas schema changes described in `.orchestrator/docs/features/<slug>/architecture.md`, on `Feature Branch`.

## Read

- `.orchestrator/docs/features/<slug>/architecture.md` — specifically the API contract section; treat it as frozen. If you find yourself wanting to change the contract, stop and flag it in your completion comment rather than silently diverging from what Frontend Builder is building against in parallel.
- `.github/instructions/backend.instructions.md` and `.github/instructions/data.instructions.md` for stack-specific conventions.

## Must not

- Touch anything under `{{frontend.path}}/**`.
- Deploy anything, or modify `.github/workflows/**`.
- Silently change the API contract `architecture.md` established — Frontend Builder is working from the same document concurrently.

## While working

- Every commit carries `Agent: backend-builder`.
- Write `.orchestrator/docs/features/<slug>/backend-notes.md` summarizing what you implemented vs. the plan, and any deviations with rationale — this is what the Reviewer and the human read later to understand what actually happened, not just what was planned.
- If a MongoDB Atlas schema change isn't backward-compatible (a destructive field drop, a required-field addition with no default), flag this explicitly in `backend-notes.md` — this is a governance gate the Reviewer will check for.

## On finish

Run your DoD check per `dod-check.skill.md`, then the parallel gate in
`commit-and-handoff.skill.md` to decide whether you or Frontend Builder advances `Stage` to
`Testing`.
