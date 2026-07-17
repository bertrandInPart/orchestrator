# Skill: DoD check (generic procedure)

The procedure every agent follows before handing off. As with DoR, the **criteria** are
stage-specific and live in [`dor-dod-definitions.md`](../../.github/instructions/dor-dod-definitions.md) —
this file only describes the mechanics.

## Procedure

1. Look up your stage's **DoD** checklist in `dor-dod-definitions.md`.
2. Evaluate each criterion against what you actually produced — not against what the plan said
   you'd produce. A criterion is only met if the artifact exists and is complete, not because you
   intended to write it.
3. If **all** criteria pass: append a `DoD: PASS` entry to the lifecycle file, then follow
   [`commit-and-handoff.skill.md`](commit-and-handoff.skill.md) to commit, advance the board, and
   post your completion comment.
4. If **any** criterion fails, follow the retry/escalation rule below.

**Not a DoD failure:** if a transient problem (API error, unavailable tool, an infra blip) kept you
from finishing your own work — not a gap in what you produced — log it with outcome `infra_error`
per `commit-and-handoff.skill.md`, stop, and let the next scheduled tick retry the stage from
scratch. Don't spend a retry/escalation cycle on something that wasn't a real quality gap.

## Retry / escalation rule

1. Read the lifecycle file's execution history. Has this stage already failed its own DoD once on
   this attempt cycle?
2. **If this is the first DoD failure:**
   - Post a comment using the "DoD failed — retrying" template in
     [`ticket-comments.skill.md`](ticket-comments.skill.md), listing exactly which criteria
     failed and why.
   - Append a `DoD: FAIL — retry #1` entry to the lifecycle file.
   - **Stop.** Do not commit, do not advance `Stage`. You'll be re-triggered on the next
     scheduled run and should fix the gap before checking DoD again.
3. **If this is the second consecutive DoD failure for this stage:**
   - Post a comment using the "Escalation" template in `ticket-comments.skill.md` (it includes the
     idempotent `blocked`-label creation step — don't skip it).
   - Set `Current Agent` to `none`, add the `blocked` label.
   - Append a `DoD: FAIL — escalated to human` entry to the lifecycle file.
   - **Stop.**

## Special case: Reviewer

Reviewer's "DoD failure" isn't a gap in its own output — it's the review finding real problems in
what upstream agents built. That's not a retry-the-same-stage case; it's a legitimate backward
transition. Follow the reviewer's own "On FAIL" section in `reviewer.chatmode.md` instead of the
generic retry rule above: set `Stage` back to `Implementation` and `Current Agent` to whichever
builder(s) need to act, rather than retrying the review itself.

## Special case: parallel builders (Backend/Frontend)

Passing your own DoD isn't enough to advance `Stage` — you also need the other builder's
completion comment to exist on the issue. See "Parallel gate" in
[`commit-and-handoff.skill.md`](commit-and-handoff.skill.md) for exactly what to do in each of the
three outcomes (both done, only you done, you fail DoD).
