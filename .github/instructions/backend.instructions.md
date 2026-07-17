---
applyTo: "server/**"
---

# Backend conventions (Node.js / Express / MongoDB Atlas)

These apply to `backend-builder` (implementation) and inform `architect` (design) and
`test-engineer` (test conventions live in `testing.instructions.md`, but the code under test
follows these rules).

## Structure

- Routes are thin: parse/validate input, call a service, shape the response. No business logic in
  route handlers.
- Services hold business logic and are the only layer that talks to Mongoose models directly.
- One Mongoose schema/model per collection, under `server/models/`. Route files under
  `server/routes/`, services under `server/services/`.

## API conventions

- REST-ish JSON APIs. Response shape for errors is always `{ "error": { "message": string, "code"?: string } }`.
- Validate all request input (body/query/params) before touching the database — reject with `400`
  on malformed input rather than letting a bad value reach Mongoose.
- Every new/changed endpoint's request/response shape must match what `architecture.md` froze for
  the feature. If you find the contract needs to change mid-implementation, stop and flag it in
  your completion comment rather than silently diverging — Frontend Builder is building against
  the same document in parallel.

## MongoDB Atlas / Mongoose

- Schema changes that aren't backward-compatible (destructive field drops, new required fields
  with no default) must be flagged explicitly in `backend-notes.md` — this is a governance gate
  the Reviewer checks for (see `security.instructions.md`).
- Use Mongoose schema validation for shape/type constraints; don't re-implement basic validation
  the schema can already express.
- Migrations/backfills for existing collections go under `migrations/`, written by
  `release-engineer`, not by `backend-builder` — your job is the schema change itself plus a note
  in `backend-notes.md` about what migration will be needed.

## Error handling

- Never let an unhandled promise rejection crash the process — every async route handler must be
  wrapped so errors reach a central error-handling middleware.
- Log server-side errors with enough context to debug (route, relevant IDs) but never log full
  request bodies that might contain PII or secrets.

## What you must not do

- Touch anything under `client/**`.
- Deploy anything, or modify `.github/workflows/**` (that's a `never`-listed path for every agent,
  see `.orchestrator/agent-boundaries.yml`).
