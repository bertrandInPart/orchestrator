# Skill: Ticket comments

The GitHub issue is where a human follows progress without reading the lifecycle file or the
board. **Post a comment at the start of your work, not only at the end** — a chain that only ever
posts "done" comments is invisible for however long each stage takes; a "starting" comment tells
the human (and any other agent reading the thread) that this stage is actively in progress right
now, not stalled.

Every comment below should be a single Markdown comment on the GitHub issue. Keep the small
metadata block at the top of each — it's what lets a future dashboard or script summarize chain
health by parsing comments instead of re-deriving state from scratch.

## 1. Starting work (post this first, right after your DoR check passes)

```markdown
### 🔧 <Agent name> — starting <Stage name>

<!-- meta: agent=<agent-name> stage=<stage> status=started timestamp=<ISO timestamp> -->

Picked up this issue. Working from [`<key input file>`](../blob/main/.orchestrator/docs/features/<slug>/<file>.md).
```

## 2. Completion (post this when your DoD passes and you're handing off)

```markdown
### ✅ <Agent name> — <Stage completed>

<!-- meta: agent=<agent-name> stage=<stage> status=done timestamp=<ISO timestamp> -->

**Summary:** <one paragraph — what you did, not just what file you wrote>

**Output:** [`.orchestrator/docs/features/<slug>/<file>.md`](../blob/main/.orchestrator/docs/features/<slug>/<file>.md)

<!-- Spec Writer only -->
**Open questions:**
1. ...
```

## 3. DoR failed — callback

```markdown
### ⚠️ <Agent name> — DoR check failed

<!-- meta: agent=<agent-name> stage=<stage> status=callback timestamp=<ISO timestamp> -->

The following Definition of Ready criteria are not met:
- <criterion>: <why it fails>

**Action:** Calling back **<previous-agent>** to fix these issues.

See [`<lifecycle file>`](../blob/main/.orchestrator/docs/features/<slug>/<lifecycle-file>.md) for tracking.
```

## 4. DoD failed — retrying

```markdown
### ⚠️ <Agent name> — DoD check failed

<!-- meta: agent=<agent-name> stage=<stage> status=retry timestamp=<ISO timestamp> -->

The following Definition of Done criteria are not met:
- <criterion>: <why it fails>

**Action:** Retrying this stage to address these gaps.
```

## 5. Escalation (DoR callback or DoD retry has failed a second time)

Before adding the `blocked` label (below), make sure it exists — it's a one-time repo setup label,
not something GitHub creates for you, and a missing label makes `gh issue edit --add-label`
fail outright:

```bash
gh label create blocked --color "B60205" --description "Escalated to a human - see on-start-checks.skill.md" 2>/dev/null || true
```

```markdown
### 🚨 <Agent name> — escalation required

<!-- meta: agent=<agent-name> stage=<stage> status=escalated timestamp=<ISO timestamp> -->

**Responsible agent:** <agent>
**Issue:** DoR/DoD criteria still not met after one callback/retry.

**Findings:**
- <criterion>: <why it still fails>

@<repo-owner> — please review and advise. `Current Agent` has been set to `none` and this issue
is labeled `blocked` until you do.

See [`<lifecycle file>`](../blob/main/.orchestrator/docs/features/<slug>/<lifecycle-file>.md) for full history.
```

## 6. Reviewer FAIL (blocking governance findings)

```markdown
### ❌ Reviewer — Governance Review: FAIL

<!-- meta: agent=reviewer stage=governance-review status=fail timestamp=<ISO timestamp> -->

**Blocking issues:**
- <rule ID>: <finding>

Sending back to **<backend-builder|frontend-builder|both>** to address. See
[`review-notes.md`](../blob/main/.orchestrator/docs/features/<slug>/review-notes.md) for the full PASS/FAIL
breakdown against every rule.
```

## 7. Scope Audit completed (Spec Auditor only)

```markdown
### 🔎 Spec Auditor — Scope Review complete

<!-- meta: agent=spec-auditor stage=scope-audit status=done timestamp=<ISO timestamp> -->

**Summary:** <one paragraph — what was audited, how many shadow spots were found, how many were
resolved in conversation vs. left open>

**Perimeter:** <one line — well-defined now, or still has open boundary questions>

**Ticket updated:** the issue description now has a `## Scope Review` section with the full
findings and resolutions.

<!-- if spec.md existed for this feature -->
**Spec synced:** [`.orchestrator/docs/features/<slug>/spec.md`](../blob/main/.orchestrator/docs/features/<slug>/spec.md) updated to match.

<!-- if any open questions remain -->
**Open questions:**
1. ...
```

## Idempotency

Before posting any comment, search the thread for an existing comment with the same `stage` +
`status` in its meta line for this attempt number. If one's already there, don't duplicate it —
this is the same idempotency principle as [`on-start-checks.skill.md`](on-start-checks.skill.md),
applied to comments specifically.
