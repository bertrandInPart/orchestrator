---
description: >
  Entry point for sending a feature back through Backend/Frontend Builder after the Reviewer
  agent's FAIL, or after a human leaves review comments on the open PR.
mode: agent
---

# Fix Review Comments

Use this when `Stage` is back at `Implementation` following a Reviewer FAIL (see
`.github/chatmodes/reviewer.chatmode.md`'s "On FAIL" section), or when a human has left comments
directly on the open PR that need addressing before merge.

## What to do

1. Read `.orchestrator/docs/features/<slug>/review-notes.md` for the specific blocking issues, and/or the PR's
   review comment thread if the human commented directly there.
2. Check `Current Agent` on the board to see whether this is Backend Builder's or Frontend
   Builder's turn (or both) — switch to the matching chatmode
   (`.github/chatmodes/backend-builder.chatmode.md` or
   `.github/chatmodes/frontend-builder.chatmode.md`) and follow it exactly, treating the blocking
   issues as the work item instead of `architecture.md` from scratch.
3. Do not re-implement anything outside what the blocking issues or PR comments actually raised —
   this is a targeted fix pass, not a re-run of the whole Implementation stage.
4. Update the relevant `*-notes.md` with what changed and why, commit with the correct `Agent:`
   trailer, and post a completion comment referencing which blocking issue(s) were addressed.
5. Once both builders (if both were implicated) have posted, this flows back through
   Test Engineer → Reviewer exactly as it did the first time — don't skip re-testing or
   re-review just because "it's just a fix."
