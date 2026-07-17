# Agent Skills

This directory holds the small, reusable procedures every chain agent (`spec-writer`,
`architect`, `backend-builder`, `frontend-builder`, `test-engineer`, `reviewer`,
`release-engineer`) invokes for the mechanical parts of its job — the parts that are identical,
or nearly identical, across every stage. A `.chatmode.md` file should describe **what makes that
stage unique** (its mandate, what it reads, what it must not do, its specific DoR/DoD criteria)
and then reference the relevant skill files for **how the surrounding mechanics work.** If you
find yourself about to paste multi-paragraph procedural prose into a chatmode file, stop — it
probably belongs here instead, written once and referenced everywhere.

| Skill | Used for |
|---|---|
| [`on-start-checks.skill.md`](on-start-checks.skill.md) | Pause switch, circuit breaker, idempotency, branch checkout, agent-mismatch detection — the first thing every agent does, every run |
| [`context-scope.skill.md`](context-scope.skill.md) | Exactly which files each stage should read (and explicitly should not), and how to pull from large shared files without loading them whole |
| [`dor-check.skill.md`](dor-check.skill.md) | The generic "check my Definition of Ready, callback-once-then-escalate" procedure |
| [`dod-check.skill.md`](dod-check.skill.md) | The generic "check my Definition of Done, retry-once-then-escalate" procedure |
| [`lifecycle-file.skill.md`](lifecycle-file.skill.md) | Creating and appending to a feature's `<issue_id>_<slug>_lifecycle.md` |
| [`ticket-comments.skill.md`](ticket-comments.skill.md) | Every comment template an agent posts, including the "starting work" comment that gives visible progress, not just the completion comment |
| [`commit-and-handoff.skill.md`](commit-and-handoff.skill.md) | Commit trailer format, moving `Stage`/`Current Agent`, telemetry logging |
| [`drift-check.skill.md`](drift-check.skill.md) | Detecting when a frozen upstream artifact (`spec.md`, `architecture.md`) was edited after its owning stage already handed it off |

**Source of truth for per-stage criteria stays in [`dor-dod-definitions.md`](../../.github/instructions/dor-dod-definitions.md).**
Skills describe the *procedure*; that file describes the *checklist content*. Don't duplicate the
checklist content into a skill file or into a chatmode — reference it.

## Why this exists

Before this directory existed, each of the 7 chatmodes carried its own ~40-line copy of the
DoR/callback and DoD/retry procedure, worded slightly differently every time. That meant fixing a
bug in the escalation logic (or changing the retry count) required editing 7 files and hoping
they stayed in sync. Now it's one file, referenced 7 times.
