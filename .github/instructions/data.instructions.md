---
applyTo: "server/models/**,migrations/**"
---

# Data conventions (MongoDB Atlas / Mongoose schemas & migrations)

Read by `architect` (schema design), `backend-builder` (schema implementation), and
`release-engineer` (migrations).

## Schema design

- Every collection has exactly one Mongoose model file under `{{backend.path}}/models/`.
- Prefer embedding for data that's always read/written together and doesn't grow unbounded;
  reference (via `ObjectId`) for data with independent lifecycle or unbounded growth. Note the
  choice and why in `architecture.md` when introducing a new collection or relationship.
- Add indexes for any field a route queries or sorts by other than `_id`. State new indexes
  explicitly in `architecture.md` — they're a migration concern (see below), not a silent side
  effect of writing a query.

## Backward compatibility (governance gate)

A schema change is backward-compatible if existing documents remain valid and readable by
old and new code during a rolling deploy. Specifically:

- **Allowed without a migration script**: adding an optional field, adding a new collection,
  widening a validation constraint.
- **Requires a migration script under `{{migrations.path}}/`**: renaming a field, narrowing/adding a
  required constraint on existing data, dropping a field, changing a field's type, splitting or
  merging collections.
- **Never do this silently**: a destructive field drop or type change with no migration path and
  no note in `backend-notes.md`. The Reviewer treats this as a blocking issue every time — see
  `security.instructions.md`'s governance checklist.

## Migrations

- One migration script per schema-changing feature, under `{{migrations.path}}/<feature-slug>-<short-desc>.js`,
  written by `release-engineer` from the notes `backend-builder` left in `backend-notes.md`.
- Migrations must be idempotent (safe to run twice) and must not assume they run against a
  database in any particular prior state beyond "the previous migration has already run."

## PII and sensitive data

- Any new field holding PII (names, emails, addresses, payment info) must be flagged in
  `architecture.md` and cited explicitly by the Reviewer against `security.instructions.md` — this
  cannot be waived by any agent, only by a named human sign-off.
