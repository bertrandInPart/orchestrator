# Case 001 — All UX states implemented

## Input

`.orchestrator/docs/features/team-comments/architecture.md` + `spec.md`'s UX Walkthrough calling for: a loading
spinner while comments fetch, an empty state ("No comments yet — be the first to say something")
when there are none, an inline error message with a retry button if the fetch fails, and the
normal comment list on success.

## Answer key — a good implementation + frontend-notes.md for this case must

- Implement all four states as distinct, visibly different UI treatments — not just a happy-path
  list with no handling for the other three.
- The error state must include the retry affordance the spec called for, not just a generic error
  message with no way to recover.
- `frontend-notes.md` must summarize what was implemented vs. the plan.
- Must not touch any file under `server/**` or any schema file.
