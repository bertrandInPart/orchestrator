---
applyTo: "**/*.test.*,**/*.spec.*,server/test/**,client/**/*.spec.ts"
---

# Testing conventions

Read primarily by `test-engineer`, whose mandate is to test against `spec.md`'s acceptance
criteria and edge cases — not just against whatever the builders happened to implement.

## What "done" means for a test plan

Every `Acceptance Criteria` block and every `Edge Cases` bullet in `spec.md` maps to one of:
1. A specific automated test (name it in `test-plan.md`), or
2. An explicit, justified note in `test-plan.md` explaining why it isn't feasible to automate
   (e.g. requires manual exploratory testing, or depends on a third-party service not mockable in
   this environment).

An implicit gap — a criterion nobody wrote a test for and nobody explained why — is treated as
worse than a documented gap. Never leave one silently.

## Backend tests

- Unit tests for services (business logic) under `server/test/unit/`, colocated by the module they
  cover.
- Integration tests for routes under `server/test/integration/`, exercising the real Express app
  against a test database (never a production or shared dev database).
- Mock external services; do not depend on live third-party APIs in CI.

## Frontend tests

- Component/service unit tests as `*.spec.ts` colocated with the file under test.
- Cover the non-happy-path UI states (`frontend.instructions.md`'s empty/loading/error/success
  requirement) — a component test suite that only covers the success state is incomplete relative
  to the spec.

## What you must not do

- Modify implementation code under `server/**` or `client/**` to make a failing test pass without
  flagging it first. A failing test against a correctly-written test is a signal for
  Backend/Frontend Builder (or a human) to fix the implementation — not something to quietly patch
  around by loosening the test's assertions.
