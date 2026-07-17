# Copilot cloud agent automations — configured and running

Per blueprint §5, the actual stage-to-stage dispatching in this chain runs through the Copilot
app's own **scheduled workflow system** (recurring jobs that start an autopilot session with a
fixed prompt on a cron schedule) rather than custom polling infrastructure. Workflows are
configured per-project through the app (not a committable YAML file), so this document is the
human-readable record of what's configured — the actual source of truth is the app's workflow
store, inspectable via the app itself.

All 6 stage-dispatch automations below are live as of this writing: every 15 minutes
(`*/15 * * * *`), running in `autopilot` mode (fully unattended), against the `orchestrator`
project, using the default model. Each one's prompt tells the agent which `Stage`/`Current Agent`
combination to look for on the Projects v2 board, which chatmode file to adopt, and which shared
instructions to follow — it's a thin dispatcher, not a reimplementation of the chatmode's logic.

There is also a 7th, non-stage automation (Automation 8 below) that runs weekly rather than every
15 minutes and never touches the board — it exists to catch chatmode/skill regressions, not to
move a feature through the chain.

## Manually-started stage — Spec Writer (deliberately no automation)

Spec Writer is **never** triggered by an automation, an event, or a schedule. It's the one stage
meant to be a real conversation: you start it yourself in Copilot Chat — either by running
`.github/prompts/new-feature.prompt.md` or switching directly to the `spec-writer` chatmode — and
describe the feature. Spec Writer then runs its full interrogation pass interactively with you
(scope, edge cases, UX, non-functional concerns) *before* anything is created. Only once you're
both satisfied does it file the GitHub issue itself (from `.github/ISSUE_TEMPLATE/feature-request.yml`,
via the API — you never need to fill out that form by hand), create the `feature/<slug>` branch,
write `spec.md`, and hand off to the `Spec Review` checkpoint.

There is deliberately no `spec-writer-on-new-issue` automation, and no trigger on `issues: opened`
for this stage — even if a human files an issue directly from the web template, nothing will
automatically start Spec Writer on it. That's intentional: it stops the chain from ever running
the first, most judgment-heavy stage unattended. If you do file an issue directly and want a spec
written for it, start Spec Writer yourself and point it at that issue number.

## Manually-started, ad-hoc — Spec Auditor (second entry point, also never automated)

Spec Auditor (`.github/chatmodes/spec-auditor.chatmode.md`, entry point
`.github/prompts/audit-spec.prompt.md`) is the second way into this chain, alongside Spec Writer —
but it never creates a ticket. Point it at an **existing** issue (one filed directly from the web
template, or one Spec Writer already wrote a spec for) and it audits that ticket instead of
drafting a new one: it confirms the feature's perimeter is actually well-defined, runs the full
shadow-spot sweep (edge cases, UX states, non-functional concerns) against the ticket's *current*
acceptance criteria, and challenges the human on every gap or contradiction it finds. Once
resolved, it appends a `## Scope Review` section to the issue description itself (not a new file)
and syncs `spec.md` if one already exists.

Like Spec Writer, there is deliberately no automation trigger for this stage — it's meant to be a
real, adversarial back-and-forth with a human, not a background pass. Unlike Spec Writer, it never
creates an issue or branch and never touches `Stage`/`Current Agent`, so it's safe to run at any
point in a feature's life — before Spec Drafting even starts, or later as a second look once
things have drifted — without disturbing where the ticket sits in the chain.

## Automation 1 — Architect (post spec approval)

- [x] **Name:** `architect-on-spec-approved`
- **Trigger:** cron `*/15 * * * *` (every 15 minutes)
- **Prompt:** for any issue with `Stage: Architecture Drafting` and `Current Agent: architect`
  (i.e. a human just re-assigned/released it past checkpoint #1), adopt
  `.github/chatmodes/architect.chatmode.md` and follow it against that issue
- **Mode:** autopilot · **Model:** default
- Includes the pause-switch and circuit-breaker checks per `.orchestrator/skills/on-start-checks.skill.md`

## Automation 2 — Backend Builder & Automation 3 — Frontend Builder (parallel, post architecture approval)

- [x] **Name:** `backend-builder-on-implementation`
- [x] **Name:** `frontend-builder-on-implementation`
- **Trigger:** cron `*/15 * * * *` (both)
- **Prompt:** for any issue with `Stage: Implementation`, adopt the respective chatmode. Each
  prompt also checks `review-notes.md` for FAIL findings first — if present, it follows
  `fix-review-comments.prompt.md` instead of the normal architecture-driven flow (this is what
  covers Automation 7 below; no separate workflow needed for that case)
- **Mode:** autopilot · **Model:** default
- Each posts its own completion comment; whichever run finds both comments present is the one
  that advances `Stage` to `Testing` (see the "Parallel gate" section of
  `.orchestrator/skills/commit-and-handoff.skill.md`)

## Automation 4 — Test Engineer

- [x] **Name:** `test-engineer-on-testing`
- **Trigger:** cron `*/15 * * * *`
- **Prompt:** for any issue with `Stage: Testing`, adopt `.github/chatmodes/test-engineer.chatmode.md`
- **Mode:** autopilot · **Model:** default

## Automation 5 — Reviewer

- [x] **Name:** `reviewer-on-governance-review`
- **Trigger:** cron `*/15 * * * *`
- **Prompt:** for any issue with `Stage: Governance Review`, adopt
  `.github/chatmodes/reviewer.chatmode.md`
- **Mode:** autopilot · **Model:** default

## Automation 6 — Release Engineer

- [x] **Name:** `release-engineer-on-release-prep`
- **Trigger:** cron `*/15 * * * *`
- **Prompt:** for any issue with `Stage: Release Prep`, adopt
  `.github/chatmodes/release-engineer.chatmode.md`
- **Mode:** autopilot · **Model:** default

## Automation 7 — Reviewer FAIL → back to builders

- [x] Folded into Automations 2/3 rather than a separate workflow — each builder's own prompt
  checks for a FAIL in `review-notes.md` on every run and switches to
  `.github/prompts/fix-review-comments.prompt.md` when it finds one, addressing the specific
  blocking issues instead of re-reading `architecture.md` from scratch. Once `Current Agent` names
  `backend-builder` or `frontend-builder` again after a FAIL, the existing scheduled workflow picks
  it up on its next 15-minute tick — no separate automation needed.

## Automation 8 — Eval sweep (regression detection, not a chain stage)

- [x] **Name:** `eval-sweep-weekly`
- **Trigger:** weekly, Mondays at 06:00
- **Prompt:** for each of the 7 chain agents, run every case in `.orchestrator/evals/<agent>/cases/` through
  that agent's chatmode in an isolated sandbox, grade the output with `eval-grader.chatmode.md`
  against `.orchestrator/evals/<agent>/rubric.yml`, append results via `.orchestrator/scripts/run-agent-evals.sh`, and open a
  PR against `develop` with the updated `.orchestrator/evals/results/**` and a pass-rate summary that calls out
  any newly-regressed criterion
- **Mode:** autopilot · **Model:** default
- This is explicitly **not** one of the 7 stage agents — it never touches a real issue, the
  Projects v2 board, or a feature branch. It exists purely to catch chatmode/skill drift on a
  schedule, independent of whether a PR happened to touch the affected files (unlike the CI
  `eval-gate` job below, which only reacts to what's visible in a given PR's own diff).
- Commits carry `Agent: eval-grader`, matching its `.orchestrator/evals/results/**`-only write path in
  `.orchestrator/agent-boundaries.yml`. It never merges its own PR.
- See `.orchestrator/evals/README.md` for the full mechanism and the CI-side `eval-gate` job
  (`.github/workflows/ci.yml`) that requires fresh eval evidence in any PR touching a chatmode,
  shared skill, or shared instructions file.

## Human-gated stages (deliberately no automation)

`Spec Review` and `Architecture Review` — no automation exists for these. Re-assigning the issue
to Copilot (or otherwise signaling approval) is both the approval and the trigger for the next
scheduled automation to pick it up. (Spec Writer itself is also never automated — see above —
but that's a different reason: it's not a review gate waiting on an automation, it's a stage that
should never run unattended at all.)

## Note on Jira projects

Everything above is written against GitHub Projects v2 field filters. If this project is
configured with `ticket_system.provider: jira` (see `.orchestrator/docs/jira-integration.md`),
these dispatch prompts need a JQL filter instead — that doc has the per-automation JQL table and
calls out the one real gap: there's no built-in cron-poller equivalent to the Copilot app's
scheduled workflows watching a JQL filter, so Jira-backed stage dispatch needs either an external
scheduler pointed at those filters, or a human manually re-running the next chatmode.

## Notes

- These are polling schedules, not event triggers — each workflow wakes up every 15 minutes,
  queries the board, and no-ops if nothing matches its `Stage`/`Current Agent` filter. Worst-case
  latency for any handoff is ~15 minutes, which is an acceptable trade-off for the simplicity of
  not needing a webhook listener.
- Keep write access to this repo limited to a small, trusted set of maintainers — this limits
  prompt-injection risk from issue content the agents read.
- Managed entirely through the app (create/update via its workflow store, run on-demand for
  testing) — there is no YAML file for these in this repo, unlike GitHub Actions workflows.
