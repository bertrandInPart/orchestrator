---
description: >
  Entry point for kicking off the agentic feature production chain from a raw feature request.
  Hands off to the Spec Writer agent (Agent 1). Always run this yourself, interactively — it is
  never triggered automatically by an issue or event (see .orchestrator/automations/README.md).
mode: agent
---

# New Feature

You are kicking off the feature production chain described in
`.github/instructions/github-workflow.instructions.md`. Switch to the **Spec Writer** chatmode
(`.github/chatmodes/spec-writer.chatmode.md`) and follow it exactly.

## Input

The user will describe a feature request, either as:
- A raw paragraph typed directly in this conversation, or
- A reference to an already-filed GitHub Issue number.

## What to do

1. Do **not** create anything yet. Whether given a raw request or an issue number, start with the
   full interrogation pass — this is meant to be a real back-and-forth conversation with the
   human, not a formality before filing a ticket.
2. Run the full interrogation pass Spec Writer's chatmode describes (scope & intent, edge cases,
   UX sense-check, non-functional pressure-testing) — do not skip categories without saying why.
   Keep going until the human is satisfied the spec reflects what they actually want, or has
   explicitly accepted remaining items as blocking open questions.
3. Only now, per Spec Writer's "On finish": if this was a raw request with no issue yet, file the
   issue from `.github/ISSUE_TEMPLATE/feature-request.yml`, derive the feature slug, create the
   `feature/<slug>` branch, and set `Feature Slug` / `Feature Branch` on the Projects board
   (`PROJECT_OWNER`/`PROJECT_NUMBER` are recorded in `github-workflow.instructions.md`). If given an
   existing issue number, skip straight to writing the spec against that issue.
4. Write `.orchestrator/docs/features/<slug>/spec.md` using the required structure.
5. Post the completion comment with open questions written out in full, move `Stage` to
   `Spec Review`, set `Current Agent` to `none`, and log telemetry.
6. Stop. Do not proceed to the Architect stage yourself — that's checkpoint #1, and it's a human's
   call.
