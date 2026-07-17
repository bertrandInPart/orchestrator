---
applyTo: "**"
---

# GitHub Ticket Workflow — Shared Instructions

Every agent in the feature chain (`spec-writer`, `architect`, `backend-builder`, `frontend-builder`, `test-engineer`, `reviewer`, `release-engineer`) follows this file for how it reads and updates a feature's GitHub Issue and Projects (v2) board entry, and for the safety mechanics (pause switch, circuit breaker, idempotency, commit tagging) that make it safe to run unattended. Individual `.chatmode.md` files reference this file rather than re-describing the mechanics themselves.

**Board reference values** (recorded once by a human after running `scripts/setup-github-project.sh`):

```
PROJECT_OWNER  = <OWNER>
PROJECT_NUMBER = <PROJECT_NUMBER>
```

> Replace the placeholders above with the real values printed at the end of `setup-github-project.sh` before this file is used by any agent.

---

## 1. The ticket model, in one paragraph

One GitHub Issue per feature, opened once from `.github/ISSUE_TEMPLATE/feature-request.yml` and never closed until the feature ships. All progress lives in two places on that same issue: a chronological thread of stage-completion comments, and custom fields on the Projects (v2) board that always reflect current truth. Agents update both. Nobody — human or agent — should ever need to ask "what stage is this feature at" in chat; it's always answerable from the board.

## 2. Board fields

- **`Stage`** (single-select, in order): `Backlog` → `Spec Drafting` → `Spec Review` → `Architecture Drafting` → `Architecture Review` → `Implementation` → `Testing` → `Governance Review` → `Release Prep` → `PR Open` → `Done`
- **`Feature Slug`** (text) — matches `docs/features/<slug>/`.
- **`Current Agent`** (single-select) — whose turn it is, or `none` while paused for a human.
- **`Feature Branch`** (text) — the single Git branch this feature's work happens on (`feature/<slug>`). Every agent checks out this exact branch — never assume or create a different one once it's set.

## 3. What every agent does, in order, every run

### 3.1 On start — do these checks in order, every single time, before anything else

1. **Check `docs/ops/CHAIN_PAUSED`.** If this file exists, stop immediately. Do not read further, do not comment, do not touch the board. This is the chain-wide kill switch — it overrides everything else in this document.
2. **Check the circuit breaker.** Count trailing `fail`/`timeout` entries for this issue + your stage in `docs/ops/agent-telemetry.jsonl` since the last `success`. If the count has reached 3, do not attempt the stage. Instead set `Current Agent` to `none`, add the `blocked` label to the issue, and post a comment summarizing the failure history and tagging a human. Stop.
3. **Idempotency check.** If this stage's output file already exists under `docs/features/<slug>/` **and** `Stage` is already at or past the value this stage produces, this is a duplicate trigger (a retried automation, a duplicate event). Do nothing further and exit — do not re-write files, do not re-post a comment, do not re-move `Stage`.
4. Resolve the issue number and `Feature Slug`/`Feature Branch` for this feature.
5. Check out `Feature Branch` exactly as recorded on the board — never a new or default branch.
6. Read the issue body and every comment added since the previous agent's comment. A human may have left clarification directly on the issue rather than waiting to be asked again — do not proceed on stale assumptions if so.
7. Note the current `Stage` and `Current Agent`. If `Current Agent` doesn't match this agent's name and the stage isn't a human-review stage the human has just released, stop and flag the mismatch rather than proceeding — this usually means the wrong agent was invoked or a previous handoff didn't complete cleanly.

### 3.2 While working

Write your stage's output file(s) under `docs/features/<slug>/` as specified in your own `.chatmode.md`, on `Feature Branch`. Do not update `Stage` mid-work — it changes exactly once, when the stage is genuinely complete.

Every commit must carry an `Agent:` trailer identifying which agent made it:

```
<commit subject>

<commit body>

Agent: backend-builder
```

This is what makes the CI boundary check (`scripts/check-agent-boundaries.sh`) able to attribute a changed file to the agent responsible for it — a commit with no trailer, or an unrecognized agent name, fails CI.

### 3.3 On finish

1. **Move `Stage` forward** to the next waiting state:
   ```bash
   ./scripts/update-ticket-stage.sh <issue-number> --field "Stage" --value "<next-stage-value>"
   ```
2. **Set `Current Agent`** — `none` if the next step is a human checkpoint, or the next agent's name if the chain continues without a human gate.
   ```bash
   ./scripts/update-ticket-stage.sh <issue-number> --field "Current Agent" --value "<next-agent-or-none>"
   ```
3. **Post one comment** using the template in §4. Before posting, search the thread for an existing comment with this stage's header — if one's already there (another idempotency signal), don't post a duplicate.
4. **Log telemetry.** Call `scripts/log-agent-run.sh` to append one line to `docs/ops/agent-telemetry.jsonl`: feature slug, issue number, agent name, stage, start/finish timestamps, duration, outcome (`success`/`fail`/`timeout`), attempt number.
5. **Never move `Stage` backward** except the Reviewer sending work back to `Implementation` on a FAIL — the one legitimate backward transition, always logged with a comment explaining why.

## 4. Comment template

```markdown
### ✅ <Agent name> — <Stage completed>

**Summary:** <one paragraph>

**Output:** [`docs/features/<slug>/<file>.md`](../blob/main/docs/features/<slug>/<file>.md)

<!-- Spec Writer only -->
**Open questions:**
1. ...

<!-- Reviewer on FAIL only -->
**Blocking issues:**
- ...
```

## 5. Parallel stages (Backend + Frontend)

Both `backend-builder` and `frontend-builder` read the same `architecture.md` and start as soon as `Stage` reaches `Implementation`. Each posts its own completion comment. Whichever finishes **second** confirms the other's comment is present before advancing `Stage` to `Testing`; if it isn't there yet, post your own comment and leave `Stage` at `Implementation` rather than advancing on a partial handoff.

## 6. Human checkpoints and the board

Checkpoints after Spec Drafting and Architecture Drafting are not gated by any GitHub-native review mechanism — approval happens out of band, and `Stage` sitting at `Spec Review` / `Architecture Review` with `Current Agent: none` is the visible pause signal. A human re-assigning the issue to Copilot is both the approval and the trigger for the next stage.

The PR-review checkpoint is GitHub-native: `release-engineer` opens the PR with `Closes #<issue-number>`, so merging closes the issue once CI carries the deploy through to `Stage: Done`.

## 7. Path boundaries

Your own `.chatmode.md` states which paths you're allowed to write to. `.github/agent-boundaries.yml` is the enforced version of that same list, checked in CI on every push via `scripts/check-agent-boundaries.sh` — treat your chatmode's stated paths as load-bearing, not descriptive, since a violation fails the build regardless of intent.
