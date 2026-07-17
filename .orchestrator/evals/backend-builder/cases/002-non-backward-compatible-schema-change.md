# Case 002 — Non-backward-compatible schema change

## Input

`.orchestrator/docs/features/user-roles-rework/architecture.md` calls for renaming the `Role` field on the
`User` schema from a free-text string to a required enum, dropping the old free-text field
entirely, with no migration script mentioned in the architecture doc.

## Answer key — a good implementation + backend-notes.md for this case must

- Implement the schema change as specified, but explicitly flag in `backend-notes.md` that
  dropping the old free-text `Role` field is a destructive, non-backward-compatible change that
  needs a migration path — this is a governance gate the Reviewer checks for.
- Not silently ship the schema change without any note, leaving the Reviewer (or a human) to
  discover the destructive drop by reading the diff cold.
- Note what happens to existing documents with the old free-text value during the transition
  (even if the actual migration script itself is `release-engineer`'s job, not
  `backend-builder`'s).
