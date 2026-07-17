---
description: >
  Second entry point into the feature production chain, alongside new-feature.prompt.md. Audits
  an EXISTING GitHub issue instead of drafting a new one — hands off to the Spec Auditor agent.
  Always run this yourself, interactively — never triggered automatically by an issue or event
  (see .orchestrator/automations/README.md).
mode: agent
---

# Audit Spec

You are auditing an existing ticket in the feature production chain described in
`.github/instructions/github-workflow.instructions.md`. Switch to the **Spec Auditor** chatmode
(`.github/chatmodes/spec-auditor.chatmode.md`) and follow it exactly.

## Input

The user will give you a reference to an already-filed GitHub Issue number or URL. If they instead
describe a brand-new feature with no issue yet, stop and redirect them to
`.github/prompts/new-feature.prompt.md` / the Spec Writer chatmode — that's a different entry
point for a different situation.

## What to do

1. Read the issue end to end (body + every comment) before saying anything about it.
2. Run Spec Auditor's context grounding pass and perimeter audit — confirm the in/out-of-scope
   boundary is actually well-defined, and sweep the ticket's current acceptance criteria against
   the full shadow-spot checklist (edge cases, UX states, non-functional concerns).
3. Challenge the human on every gap or contradiction you find, specifically and one at a time —
   don't accept a restated gap as a resolution. Keep going until each finding is resolved or
   explicitly logged as a blocking open question.
4. Per Spec Auditor's "On finish": append a `## Scope Review` section to the issue description via
   the GitHub API (never overwrite existing content), sync `.orchestrator/docs/features/<slug>/spec.md`
   if one already exists, post the completion comment with any remaining open questions written
   out in full, and append a lifecycle entry only if a lifecycle file already exists.
5. Do **not** create an issue, create a branch, or touch `Stage`/`Current Agent` on the Projects
   board — those are Spec Writer's and the chain's job, not yours.
6. Stop. This is a standalone audit pass, not a stage in the automated chain — it doesn't hand off
   to another agent itself.
