# Case 001 — Standard CRUD-ish feature with resolved spec

## Input

`.orchestrator/docs/features/team-comments/spec.md` (approved, all Open Questions answered): a feature letting
any project member post/edit/delete their own comments on a project, visible to all project
members, with pagination beyond 50 comments, and soft-delete (comment shows "[deleted]" rather
than disappearing).

## Answer key — a good architecture.md for this case must

- Name the specific new Angular component(s) (e.g. a comment list + comment form) and Express
  route(s)/service(s) and Mongoose collection (e.g. a `Comment` model referencing `projectId` and
  `authorId`).
- Freeze the API contract: e.g. `POST /api/projects/:id/comments`, `PATCH
  /api/comments/:id`, `DELETE /api/comments/:id` (soft) with explicit request/response shapes.
- State explicitly where soft-delete is enforced (e.g. a `deletedAt` field + query filter, not a
  real document removal).
- State explicitly where pagination is handled (query params, response shape) since the spec
  called for it.
- State where "only the author can edit/delete their own comment" is enforced (route
  middleware/service layer check).
- NOT contain actual route handler code or component templates — only the design.
