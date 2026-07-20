---
applyTo: "**"
---

# Security & governance rules

This is the enforcement point for governance-as-code referenced by `reviewer.chatmode.md`. Every
rule below must produce an explicit PASS/FAIL line in `.orchestrator/docs/features/<slug>/review-notes.md` — not
a general "looks fine" summary. Rules a feature doesn't touch get `not applicable`, stated
explicitly, not omitted.

## Rules

### R1 — PII handling
Any change that introduces, reads, or transforms user PII (names, emails, addresses, phone
numbers, payment/financial info, government IDs, health data) must:
- Be flagged explicitly in `architecture.md` when the feature was designed.
- Be cited by file/field in `review-notes.md`, with a named human required to sign off in the PR
  before merge. No agent may waive this requirement regardless of how minor the field looks.

### R2 — Secrets and connection strings
No secret, API key, connection string, or credential may appear in any file in the diff — source
code, config, test fixtures, or committed logs. This is also checked by CI's secret-scan step; the
Reviewer calls it out explicitly if seen, rather than assuming CI alone will catch it.

### R3 — Auth boundaries
Any change to an authenticated route, permission check, or session-handling logic must be
reviewed for:
- Whether an unauthenticated request is correctly rejected.
- Whether a user with permission on an object but not the specific action is correctly rejected
  (not just "is logged in").
- Whether a session expiring mid-action fails safely (no partial state left inconsistent).

### R4 — Schema migration safety
Per `data.instructions.md`: any destructive field drop, type change, or new required field without
a default on an existing MongoDB Atlas collection must have a documented migration path under
`{{migrations.path}}/`. Absence of one is a blocking issue, not a suggestion.

### R5 — Dependency risk
Any new third-party dependency introduced by `backend-builder` or `frontend-builder` should be
noted in the relevant `*-notes.md` with a one-line justification. The Reviewer flags any dependency
that duplicates functionality already available in the codebase, or that hasn't been justified.

### R6 — Path boundaries (second layer)
The Reviewer independently checks that the diff stays within each prior agent's stated write
paths (`{{backend.path}}/**` for Backend Builder, `{{frontend.path}}/**` for Frontend Builder, test paths for Test
Engineer). This is a second, human-readable layer behind the CI-enforced check in
`.orchestrator/scripts/check-agent-boundaries.sh` — not a replacement for it.

## What the Reviewer's PASS does NOT mean

A PASS from the Reviewer agent is advisory context for the human merging the PR, not a merge gate
by itself. The actual automated merge gate is CI: lint, tests, secret-scan, and
`.orchestrator/scripts/check-agent-boundaries.sh`. The Reviewer never merges or approves the PR.
