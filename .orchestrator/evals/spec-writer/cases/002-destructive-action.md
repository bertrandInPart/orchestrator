# Case 002 — Destructive action

## Input (what the Spec Writer agent receives)

> Feature name: "Bulk delete old reports"
> Description: "Add a button that lets an admin delete all reports older than 90 days in one
> click, to keep the reports list clean."
> Requester: ops team
> Priority: Low

## Answer key — a good spec.md for this case must

- Explicitly ask, as an Open Question, whether this delete is permanent or should be
  recoverable/undoable (e.g. soft-delete, a trash/archive period) — must not silently assume
  either answer.
- Explicitly ask whether the admin gets a confirmation step (e.g. "you are about to delete N
  reports — are you sure?") before the bulk delete executes.
- Raise, as an edge case, what happens if the delete is triggered while another user is actively
  viewing/editing one of the reports about to be deleted.
- Raise, as an edge case, partial-failure behavior: what happens if the bulk delete fails partway
  through (some reports deleted, some not)?
- Ask about audit/logging expectations, given this is a destructive bulk admin action.
- NOT propose a specific deletion mechanism (e.g. a MongoDB TTL index, a specific `findOneAndDelete`
  call) — that's the Architect's job, not the spec's.
