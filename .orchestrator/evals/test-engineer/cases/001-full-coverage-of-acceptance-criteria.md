# Case 001 — Full coverage of acceptance criteria and edge cases

## Input

`.orchestrator/docs/features/team-comments/spec.md` with 4 Acceptance Criteria blocks (post/edit/delete own
comment, view all project comments) and 5 Edge Cases (empty state, pagination boundary at 50
comments, unauthenticated access, editing a comment that was deleted by someone else concurrently,
oversized comment body).

## Answer key — a good test-plan.md for this case must

- Map every one of the 4 acceptance criteria to a named test.
- Map every one of the 5 edge cases to a named test, OR state explicitly why one isn't feasible to
  automate (e.g. the concurrent-delete race condition might require an explicit note about manual
  verification if the test harness can't easily simulate it) — an unaddressed edge case with no
  note at all is a failing grade regardless of how many other tests exist.
- Not restrict itself to testing implementation details that happen to exist in the code but
  aren't traceable back to a specific acceptance criterion or edge case.
