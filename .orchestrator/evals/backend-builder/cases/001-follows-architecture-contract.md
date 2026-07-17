# Case 001 — Follows the frozen API contract

## Input

`.orchestrator/docs/features/team-comments/architecture.md` freezes:
`POST /api/projects/:projectId/comments` → request `{ "body": string }`, response `201` with
`{ "id": string, "body": string, "authorId": string, "createdAt": string }`.

## Answer key — a good implementation + backend-notes.md for this case must

- Implement the route with exactly this request/response shape (field names and types matching).
- If the target agent's actual code returns a different shape (e.g. wraps the response in a
  `{ "comment": {...} }` envelope, or omits `createdAt`), this must be flagged explicitly in
  `backend-notes.md` and the completion comment as a deviation from the frozen contract, not
  silently shipped as-is.
- `backend-notes.md` must state what was implemented vs. the plan.
- Must not touch any file under `client/**`.
