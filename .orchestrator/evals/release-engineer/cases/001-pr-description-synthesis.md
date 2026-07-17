# Case 001 — PR description synthesis

## Input

All of `.orchestrator/docs/features/team-comments/`: `spec.md`, `architecture.md`, `backend-notes.md`,
`frontend-notes.md`, `test-plan.md` (all tests passing), `review-notes.md` (PASS, no blocking
issues).

## Answer key — a good PR description for this case must

- Follow the required shape (Summary, Spec highlights, Architecture, Testing, Governance review,
  Migration notes if applicable) with real synthesized content in each section, not placeholder
  text or bare links.
- Include `Closes #<issue-number>`.
- Be readable end-to-end by a human who has not been following the issue thread — i.e. it
  shouldn't assume context only available by opening every linked doc.
