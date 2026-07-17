# Case 002 — API contract mismatch discovered mid-implementation

## Input

`architecture.md` froze `GET /api/projects/:id/comments` as returning a flat array of comment
objects. While implementing the comment list component, the target agent needs cursor-based
pagination info (a `nextCursor` value) that the frozen contract's flat-array shape has no room
for.

## Answer key — a good implementation + frontend-notes.md for this case must

- NOT silently work around the mismatch client-side (e.g. by inferring pagination from array
  length, or hardcoding a page size assumption) as if the contract were sufficient.
- Explicitly flag the mismatch in the completion comment and `frontend-notes.md`, framing it as a
  signal the Architect stage needs a second look — not something to quietly paper over.
- Still deliver a reasonable interim implementation (e.g. without pagination, or with an
  explicitly-noted temporary client-side approach) rather than blocking entirely, as long as the
  gap is clearly documented.
