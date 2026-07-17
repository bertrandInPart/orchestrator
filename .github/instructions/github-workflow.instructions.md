---
applyTo: "**"
---

# GitHub Ticket Workflow — Shared Instructions

Every agent in the feature chain (`spec-writer`, `architect`, `backend-builder`, `frontend-builder`, `test-engineer`, `reviewer`, `release-engineer`) follows this file for the ticket **model** (what the board fields mean, what the ticket represents) and points to `.orchestrator/skills/` for the **mechanics** (how to actually perform each recurring step). This file is policy; `.orchestrator/skills/` is procedure — don't duplicate mechanics back into this file if you're editing it.

**Board reference values** (recorded once by a human after running `.orchestrator/scripts/setup-github-project.sh`):

```
PROJECT_OWNER  = <PROJECT_OWNER>
PROJECT_NUMBER = <PROJECT_NUMBER>
```

> Board URL: https://github.com/users/<PROJECT_OWNER>/projects/<PROJECT_NUMBER> — created via
> `.orchestrator/scripts/setup-github-project.sh` (run directly against the GitHub API/CLI; see
> `.orchestrator/docs/ops/bot-identity.md` for the credential note, and adjust for an
> organization-owned board if `<PROJECT_OWNER>` is an org rather than a user). Fields created:
> `Stage`, `Feature Slug`, `Current Agent`, `Feature Branch`.

---

## 1. The ticket model, in one paragraph

One GitHub Issue per feature, opened once — either directly by a human filling out `.github/ISSUE_TEMPLATE/feature-request.yml`, or by Spec Writer itself (same template shape, filed via the API) at the end of an interactive spec-drafting conversation it had with a human (see `spec-writer.chatmode.md` and `.orchestrator/automations/README.md`) — and never closed until the feature ships. Either way, the issue is never opened before that conversation/interrogation pass is done; the ticket only exists once there's a real spec behind it. All progress lives in three places on that same issue, and they must never disagree: a chronological thread of stage-start and stage-completion comments, custom fields on the Projects (v2) board, and the feature's lifecycle file (`.orchestrator/docs/features/<slug>/<issue_id>_<slug>_lifecycle.md`) — **the lifecycle file is the source of truth** for DoR/DoD history; the board and the comments are human-readable mirrors of it. Nobody — human or agent — should ever need to ask "what stage is this feature at" in chat; it's always answerable from the board, and "why did it get here" is always answerable from the lifecycle file.

## 2. Board fields

- **`Stage`** (single-select, in order): `Backlog` → `Spec Drafting` → `Spec Review` → `Architecture Drafting` → `Architecture Review` → `Implementation` → `Testing` → `Governance Review` → `Release Prep` → `PR Open` → `Done`
- **`Feature Slug`** (text) — matches `.orchestrator/docs/features/<slug>/`.
- **`Current Agent`** (single-select) — whose turn it is, or `none` while paused for a human.
- **`Feature Branch`** (text) — the single Git branch this feature's work happens on (`feature/<slug>`). Every agent checks out this exact branch — never assume or create a different one once it's set.

## 3. What every agent does, in order, every run — see `.orchestrator/skills/`

1. **On start:** [`skills/on-start-checks.skill.md`](../../.orchestrator/skills/on-start-checks.skill.md), then [`skills/dor-check.skill.md`](../../.orchestrator/skills/dor-check.skill.md).
2. **While working:** [`skills/context-scope.skill.md`](../../.orchestrator/skills/context-scope.skill.md) for what to read, [`skills/ticket-comments.skill.md`](../../.orchestrator/skills/ticket-comments.skill.md) for the "starting work" comment posted once DoR passes. Do not update `Stage` mid-work — it changes exactly once, when the stage is genuinely complete.
3. **On finish:** [`skills/dod-check.skill.md`](../../.orchestrator/skills/dod-check.skill.md), then [`skills/commit-and-handoff.skill.md`](../../.orchestrator/skills/commit-and-handoff.skill.md) for the commit trailer, board move, telemetry, and completion comment.

The per-stage DoR/DoD **criteria** (as opposed to the check *procedure*, which is in the skills above) live in [`dor-dod-definitions.md`](dor-dod-definitions.md).

## 4. Parallel stages (Backend + Frontend)

Both `backend-builder` and `frontend-builder` read the same `architecture.md` and start as soon as `Stage` reaches `Implementation`. See the "Parallel gate" section of [`skills/commit-and-handoff.skill.md`](../../.orchestrator/skills/commit-and-handoff.skill.md) for exactly how they decide, without colliding, which one advances `Stage` to `Testing`.

## 5. Human checkpoints and the board

Checkpoints after Spec Drafting and Architecture Drafting are not gated by any GitHub-native review mechanism — approval happens out of band, and `Stage` sitting at `Spec Review` / `Architecture Review` with `Current Agent: none` is the visible pause signal. A human re-assigning the issue to Copilot is both the approval and the trigger for the next stage.

The PR-review checkpoint is GitHub-native: `release-engineer` opens the PR with `Closes #<issue-number>`, so merging closes the issue once CI carries the deploy through to `Stage: Done`.

## 6. Spec Auditor (ad-hoc, not a chain stage)

`spec-auditor` is a second, human-invoked entry point (see `.orchestrator/automations/README.md`) that
audits an **existing** issue's scope instead of drafting a new one. It appends a `## Scope Review`
section to the issue description and, if `spec.md` already exists, syncs it — but it never creates
an issue/branch and never moves `Stage`/`Current Agent`. It isn't one of the seven chain agents
above and has no row in the `Stage` progression; treat any `## Scope Review` section on an issue as
additional context to read, not a signal that the chain has advanced.

## 7. Path boundaries

Your own `.chatmode.md` states which paths you're allowed to write to. `.orchestrator/agent-boundaries.yml` is the enforced version of that same list, checked in CI on every push via `.orchestrator/scripts/check-agent-boundaries.sh` — treat your chatmode's stated paths as load-bearing, not descriptive, since a violation fails the build regardless of intent.
