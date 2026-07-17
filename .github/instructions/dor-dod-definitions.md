# Definition of Ready (DoR) & Definition of Done (DoD) — All Agents

## Stage 1: Spec Writer

### DoR (on start)
- ✅ Raw feature request provided OR existing issue number provided
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ For existing issues: no spec exists yet, OR spec exists but `Stage` is still `Spec Drafting` (not yet reviewed)

### DoD (before handoff)
- ✅ `.orchestrator/docs/features/<slug>/spec.md` exists and is complete:
  - ✅ Existing Context: states either "no existing implementation in this domain (greenfield)"
    or what existing code/behavior was checked during the context grounding pass, and any
    correction it produced against a stale assumption or memory entry
  - ✅ Problem Statement: clearly articulates the user problem and success criteria
  - ✅ User Stories: at least one "As a ___, I want ___, so that ___"
  - ✅ UX Walkthrough: step-by-step flow including empty/loading/error/success states
  - ✅ Acceptance Criteria: at least 3 Given/When/Then blocks
  - ✅ Edge Cases: at least 5 identified and articulated
  - ✅ Explicitly Out of Scope: non-empty section
  - ✅ Open Questions: either empty (all answered) OR explicitly accepted as blocking by human
- ✅ GitHub issue filed (if it didn't already exist)
- ✅ `feature/<slug>` branch created
- ✅ `Feature Slug` and `Feature Branch` set on board
- ✅ Lifecycle file created: `.orchestrator/docs/features/<slug>/<issue_id>_<slug>_lifecycle.md`
- ✅ `spec.md` artifact hash recorded in the lifecycle file (see `drift-check.skill.md`)

---

## Stage 2: Architect

### DoR (on start)
- ✅ `.orchestrator/docs/features/<slug>/spec.md` exists and is complete (all DoD criteria above met)
- ✅ `spec.md`'s current content hash matches the hash recorded at Spec Writer's DoD (drift check —
  see `drift-check.skill.md`)
- ✅ GitHub issue exists with `Stage: Architecture Drafting` and `Current Agent: architect`
- ✅ All "Open Questions" in spec are either answered (in issue comments) or explicitly marked as "not blocking this stage"
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists

### DoD (before handoff)
- ✅ `.orchestrator/docs/features/<slug>/architecture.md` exists:
  - ✅ Component/route/schema breakdown: lists all new/modified Angular components, Express routes, Mongoose schemas
  - ✅ Frozen API contract: request/response shapes explicitly documented
  - ✅ Edge-case mapping: every edge case from spec.md has a corresponding note on how it's handled (validation, schema, UI state)
  - ✅ Migration notes (if applicable): destructive changes documented with rollback strategy
  - ✅ Session-sizing note: assessment of whether work fits in one agent session
- ✅ No contradictions with `spec.md` acceptance criteria or open questions
- ✅ Lifecycle file updated with DoR/DoD check results
- ✅ `architecture.md` artifact hash recorded in the lifecycle file (see `drift-check.skill.md`)

---

## Stage 3a: Backend Builder

### DoR (on start)
- ✅ `.orchestrator/docs/features/<slug>/architecture.md` exists and meets all DoD criteria above
- ✅ `architecture.md`'s current content hash matches the hash recorded at Architect's DoD (drift
  check — see `drift-check.skill.md`)
- ✅ GitHub issue exists with `Stage: Implementation` and `Current Agent: backend-builder`
- ✅ `feature/<slug>` branch exists and is checked out
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists

### DoD (before handoff)
- ✅ All Express routes/Node services defined in architecture.md are implemented
- ✅ All Mongoose schema changes defined in architecture.md are applied (with migrations if destructive)
- ✅ API contract matches architecture.md exactly (no unexpected changes)
- ✅ `.orchestrator/docs/features/<slug>/backend-notes.md` exists and documents:
  - ✅ What was implemented vs. plan
  - ✅ Any deviations with rationale
  - ✅ Destructive schema changes flagged (if any)
- ✅ All commits carry `Agent: backend-builder` trailer
- ✅ Lifecycle file updated with DoR/DoD check results
- ✅ (Parallel gate) If Frontend Builder's completion comment exists, advance `Stage` to `Testing`; otherwise leave it at `Implementation`

---

## Stage 3b: Frontend Builder

### DoR (on start)
- ✅ `.orchestrator/docs/features/<slug>/architecture.md` exists and meets all DoD criteria above
- ✅ `architecture.md`'s current content hash matches the hash recorded at Architect's DoD (drift
  check — see `drift-check.skill.md`)
- ✅ GitHub issue exists with `Stage: Implementation` and `Current Agent: frontend-builder`
- ✅ `feature/<slug>` branch exists and is checked out
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists

### DoD (before handoff)
- ✅ All Angular components/services defined in architecture.md are implemented
- ✅ All UI screens match the UX Walkthrough in spec.md (empty/loading/error/success states)
- ✅ API contract matches architecture.md exactly (no unexpected changes)
- ✅ `.orchestrator/docs/features/<slug>/frontend-notes.md` exists and documents:
  - ✅ What was implemented vs. plan
  - ✅ Any deviations with rationale
- ✅ All commits carry `Agent: frontend-builder` trailer
- ✅ Lifecycle file updated with DoR/DoD check results
- ✅ (Parallel gate) If Backend Builder's completion comment exists, advance `Stage` to `Testing`; otherwise leave it at `Implementation`

---

## Stage 4: Test Engineer

### DoR (on start)
- ✅ Both `backend-notes.md` and `frontend-notes.md` exist (Backend & Frontend Builder completion comments are both on issue)
- ✅ GitHub issue exists with `Stage: Testing` and `Current Agent: test-engineer`
- ✅ `feature/<slug>` branch exists with all implementation commits
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists

### DoD (before handoff)
- ✅ `.orchestrator/docs/features/<slug>/test-plan.md` exists:
  - ✅ Every acceptance criterion from spec.md has a corresponding test (passing or documented as non-feasible with rationale)
  - ✅ Every edge case from spec.md has a corresponding test (passing or documented as non-feasible with rationale)
  - ✅ At least one integration test that exercises the full feature end-to-end
  - ✅ All tests pass (green CI)
- ✅ No implementation code modified outside allowed test paths without flagging in comment
- ✅ All commits carry `Agent: test-engineer` trailer
- ✅ Lifecycle file updated with DoR/DoD check results

---

## Stage 5: Reviewer

### DoR (on start)
- ✅ `test-plan.md` exists and all tests are passing
- ✅ GitHub issue exists with `Stage: Governance Review` and `Current Agent: reviewer`
- ✅ `feature/<slug>` branch exists with all implementation + test commits
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists
- ✅ `.github/instructions/security.instructions.md` governance rules R1–R6 are applicable and will be checked

### DoD (before handoff)
- ✅ `.orchestrator/docs/features/<slug>/review-notes.md` exists:
  - ✅ Every security rule (R1–R6) has explicit PASS/FAIL/NOT APPLICABLE entry
  - ✅ Any PII handling flagged and requires human sign-off (named in PR comment)
  - ✅ No secrets/API keys in diff
  - ✅ Auth boundaries correctly enforced (unauthenticated rejection, permission checks, session expiry)
  - ✅ Destructive schema migrations have rollback documented (if applicable)
  - ✅ All new dependencies justified
  - ✅ Code stays within stated agent boundaries (Backend ⊆ `server/**`, Frontend ⊆ `client/**`, Tests ⊆ allowed paths)
- ✅ If any FAIL found: post blocking comment, set `Current Agent` back to responsible builder (backend/frontend), log callback attempt
- ✅ If all PASS: Lifecycle file updated, prepare to open PR

---

## Stage 6: Release Engineer

### DoR (on start)
- ✅ `review-notes.md` exists with all PASS/NOT APPLICABLE (no FAIL)
- ✅ GitHub issue exists with `Stage: Release Prep` and `Current Agent: release-engineer`
- ✅ `feature/<slug>` branch exists with all commits (spec → impl → tests → review)
- ✅ `.orchestrator/docs/ops/CHAIN_PAUSED` does not exist
- ✅ Lifecycle file exists

### DoD (before handoff)
- ✅ PR opened against main/master:
  - ✅ PR title is clear and descriptive
  - ✅ PR body links issue with `Closes #<issue>`
  - ✅ PR description summarizes changes: spec → architecture → implementation → tests
- ✅ CI is green (lint, test, secret-scan, agent-boundaries)
- ✅ No merge conflicts
- ✅ All commits carry `Agent: <responsible>` trailers (Spec Writer, Architect, Backend/Frontend Builders, Test Engineer)
- ✅ Lifecycle file updated with DoR/DoD check results
- ✅ (No further handoff; merge is human's call or automated based on repo settings)

---

## Procedure pointers (not restated here — this file is criteria only)

The mechanics of checking these criteria and what to do on failure — callback-once-then-escalate
for DoR, retry-once-then-escalate for DoD, the parallel-builder special case, drift checks against
frozen upstream artifacts, and the lifecycle file's structure — all live in `.orchestrator/skills/`, not
here, so there's exactly one place to fix a bug in that logic instead of two drifting copies:

- [`dor-check.skill.md`](../../.orchestrator/skills/dor-check.skill.md)
- [`dod-check.skill.md`](../../.orchestrator/skills/dod-check.skill.md)
- [`drift-check.skill.md`](../../.orchestrator/skills/drift-check.skill.md)
- [`lifecycle-file.skill.md`](../../.orchestrator/skills/lifecycle-file.skill.md)

