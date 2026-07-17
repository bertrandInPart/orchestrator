# Skill: Lifecycle file

Every feature has exactly one lifecycle file: `.orchestrator/docs/features/<slug>/<issue_id>_<slug>_lifecycle.md`.
It is the **source of truth** for DoR/DoD history and callback/escalation/retry counts — not the
issue comments (those are a human-readable mirror of it, not the record itself) and not your own
memory of what happened on a previous run, since you have none.

## Creating it (Spec Writer, first run only)

Spec Writer creates this file once, at the same time it files the issue. Structure:

```markdown
# Lifecycle: Issue #<issue_id> — <slug>

**Created:** <ISO timestamp>
**Last Updated:** <ISO timestamp>

## DoR/DoD Definitions (reference)

See `.github/instructions/dor-dod-definitions.md` for the full checklist per stage — not
duplicated here, so this file never goes stale relative to the actual criteria.

## Execution History

(entries appended below, oldest first)
```

No other agent creates this file. If you're not Spec Writer and this file doesn't exist, that's a
DoR failure (see `dor-check.skill.md`) — call back Spec Writer, don't create it yourself.

## Appending to it (every agent, every check)

Append one entry per check, in this shape, and update the `**Last Updated**` timestamp at the top:

```markdown
### <Agent name> — Attempt <n> — <ISO timestamp>

- **Check:** DoR | DoD
- **Result:** PASS | FAIL | CALLBACK | RETRY | ESCALATED
- **Details:** <which criteria failed and why, or "all criteria met">
- **Action taken:** <e.g. "Called back architect (attempt #1)" / "Advanced Stage to Testing" / "Escalated to human">
```

Append an entry for:
- Every DoR check (pass or fail)
- Every DoD check (pass or fail) — include an `Artifact hash` line per primary output file per
  [`drift-check.skill.md`](drift-check.skill.md), so downstream stages can detect if it's edited
  after the fact
- Every callback, retry, or escalation decision

Never rewrite or delete prior entries — this file is an append-only audit trail. If you need to
know "has X already been called back once," read the history; don't trust a summary field that
could drift from the actual entries.

## Committing it

The lifecycle file is committed alongside your other output, with the same `Agent:` trailer, per
[`commit-and-handoff.skill.md`](commit-and-handoff.skill.md) — commit it at every step, not just
at the end of your stage, so a mid-stage failure still leaves a readable trail.

## Spec Auditor (ad-hoc, not a chain stage)

Spec Auditor (`spec-auditor.chatmode.md`) is a human-invoked audit pass on an existing ticket, not
a chain stage — it doesn't create this file. If a lifecycle file already exists for the feature
being audited, append one entry per audit using the same shape as above, with `**Check:**` set to
`Scope Audit` and `**Result:**` set to `RESOLVED` (every finding was answered) or `OPEN QUESTIONS
REMAIN`. If no lifecycle file exists yet (e.g. the issue was filed directly, never through Spec
Writer), skip this step entirely — don't create one on Spec Auditor's behalf.
