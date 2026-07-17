# Skill: DoR check (generic procedure)

This is the procedure every agent except Spec Writer's first-ever run follows to check its
Definition of Ready. The **criteria themselves** are stage-specific and live in
[`dor-dod-definitions.md`](../../.github/instructions/dor-dod-definitions.md) — this file only describes the
mechanics of checking them and what to do on failure. Don't restate the criteria here or in your
chatmode; look them up.

## Procedure

1. Look up your stage's **DoR** checklist in `dor-dod-definitions.md`.
2. Evaluate each criterion against real state (files that exist, board field values, issue
   comments) — not against what you assume should be true. Where a criterion references an
   upstream artifact staying frozen (e.g. `spec.md`, `architecture.md`), also run the drift check
   in [`drift-check.skill.md`](drift-check.skill.md) against it, not just a mere existence check.
3. If **all** criteria pass: append a `DoR: PASS` entry to the lifecycle file (see
   [`lifecycle-file.skill.md`](lifecycle-file.skill.md)) and proceed to your mandate.
4. If **any** criterion fails, follow the callback/escalation rule below.

**Not a DoR failure:** if you can't even *evaluate* a criterion because of a transient problem
(the GitHub API errored, a tool was unavailable, a file read failed for reasons unrelated to the
file's actual content) — that's an infra error, not a DoR failure. Log it with outcome
`infra_error` per `commit-and-handoff.skill.md`, stop, and let the next scheduled tick retry. Don't
call back the previous agent over something that isn't their fault.

## Callback / escalation rule

1. Read the lifecycle file's execution history. Has the previous agent in the chain already been
   called back once, for this same DoR failure, at this stage?
2. **If not yet called back:**
   - Post a comment using the "DoR failed — callback" template in
     [`ticket-comments.skill.md`](ticket-comments.skill.md), listing exactly which criteria
     failed and why.
   - Set `Current Agent` to the previous agent in the chain.
   - Append a `DoR: FAIL — callback #1 to <previous-agent>` entry to the lifecycle file.
   - **Stop.** Do not proceed with your own stage's work.
3. **If already called back once and it still fails:**
   - Post a comment using the "Escalation" template in `ticket-comments.skill.md` (it includes the
     idempotent `blocked`-label creation step — don't skip it).
   - Set `Current Agent` to `none`, add the `blocked` label.
   - Append a `DoR: FAIL — escalated to human` entry to the lifecycle file.
   - **Stop.**

## Special case: parallel builders (Backend/Frontend) calling back the Architect

Backend Builder and Frontend Builder share one upstream dependency (`architecture.md`) but run in
parallel. If both discover a DoR problem with `architecture.md` independently:

- Whichever one calls back the Architect first logs the callback attempt in the shared lifecycle
  file.
- The other builder, on its own DoR check, must read the lifecycle file **before** calling back
  again — if a callback to Architect is already logged for this issue, don't log a second one;
  either wait for the Architect's fix or, if Architect was already called back once and failed
  again, escalate directly rather than issuing a redundant second callback.

## Special case: Test Engineer

Test Engineer doesn't call back a single previous agent on DoR failure — its DoR depends on
*both* parallel builders finishing. If DoR fails because one or both notes files are missing,
leave `Current Agent` at `test-engineer` (the builders will advance the stage themselves once
both are done) rather than calling anyone back. Only escalate if this wait has clearly stalled
(check `agent-telemetry.jsonl` timestamps) — that's what the circuit breaker in
`on-start-checks.skill.md` and `chain-health.yml` are for.
