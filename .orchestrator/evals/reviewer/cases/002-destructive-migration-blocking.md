# Case 002 — Destructive migration without a documented path

## Input

`backend-notes.md` mentions in passing that the `legacyStatus` field was removed from the `Order`
schema "since it's no longer used," with no migration script under `migrations/` and no note about
what happens to existing documents that still have that field.

## Answer key — a good review-notes.md for this case must

- Treat this as a blocking issue (per rule R4), not a non-blocking suggestion — a destructive
  field drop with no documented migration path fails outright regardless of how minor the
  justification sounds.
- State the specific missing artifact (a migration script under `migrations/`) rather than a vague
  "should probably migrate this."
- Not let confident-sounding rationale in `backend-notes.md` ("no longer used") substitute for
  an actual backward-compatibility check.
