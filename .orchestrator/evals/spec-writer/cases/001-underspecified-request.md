# Case 001 — Underspecified request

## Input (what the Spec Writer agent receives)

> Feature name: "Team comments"
> Description: "Users should be able to leave comments on a project so the team can discuss it."
> Requester: self
> Priority: Medium

## Answer key — a good spec.md for this case must

- Ask, as an open question, who can see/post comments (all team members? project owners only?
  external guests if the app has them?) — the request doesn't say.
- Ask about the empty state (no comments yet) and roughly expected volume/pagination for a
  long-running discussion thread.
- Ask whether comments can be edited or deleted after posting, and if so, whether that's
  destructive/needs confirmation — the request doesn't address this at all.
- Ask about notification behavior (does anyone get notified of a new comment?) since this is a
  plausible but unstated expectation for a "discussion" feature.
- Not assume any of the above and mark the spec "ready" — these must land in Open Questions, not
  be silently decided.
- NOT propose implementation details (e.g. "use a Comment collection with a projectId field",
  "add a POST /projects/:id/comments route") — that's the Architect's job.
