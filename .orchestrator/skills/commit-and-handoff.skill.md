# Skill: Commit & handoff

The mechanics of finishing a stage, once your DoD check has passed. This is the same for every
agent; only the specific `Stage`/`Current Agent` values you set differ (given in your own
chatmode).

## Commit format

Every commit carries an `Agent:` trailer identifying which agent made it:

```
<commit subject>

<commit body>

Agent: <your-agent-name>
```

This is what lets the CI boundary check (`.orchestrator/scripts/check-agent-boundaries.sh`) attribute a changed
file to the agent responsible for it — a commit with no trailer, or an unrecognized agent name,
fails CI. Commit your output files and the lifecycle file together where practical, so a single
commit tells the whole story of "what changed and why the lifecycle says it passed."

## Moving the board

```bash
./.orchestrator/scripts/update-ticket-stage.sh <issue-number> --field "Stage" --value "<next-stage-value>"
./.orchestrator/scripts/update-ticket-stage.sh <issue-number> --field "Current Agent" --value "<next-agent-or-none>"
```

- Set `Current Agent` to `none` if the next step is a human checkpoint; otherwise the next agent's
  name.
- **Never move `Stage` backward** except the Reviewer sending work back to `Implementation` on a
  FAIL (see the "Special case: Reviewer" note in
  [`dod-check.skill.md`](dod-check.skill.md)) — always logged with a comment explaining why.
- `Stage` changes exactly once per successful stage completion — don't update it mid-work.

## Parallel gate (Backend Builder / Frontend Builder only)

Both of you read the same `architecture.md` and start as soon as `Stage` reaches
`Implementation`. Neither of you unilaterally owns advancing the stage:

1. Pass your own DoD check (writes `backend-notes.md` or `frontend-notes.md`, commits, updates
   lifecycle file).
2. Check whether the *other* builder's completion comment already exists on the issue.
3. **If it exists:** you're the second to finish — advance `Stage` to `Testing` and
   `Current Agent` to `test-engineer` yourself, then post your completion comment.
4. **If it doesn't exist yet:** post your completion comment, but leave `Stage` at
   `Implementation` and leave `Current Agent` unchanged — the other builder will advance it when
   it finishes.

## Telemetry

Call `.orchestrator/scripts/log-agent-run.sh` to append one line to `.orchestrator/docs/ops/agent-telemetry.jsonl`: feature
slug, issue number, agent name, stage, start/finish timestamps, duration, outcome, attempt number.
Do this on every terminal outcome of a run — not only on success; the circuit breaker in
[`on-start-checks.skill.md`](on-start-checks.skill.md) depends on failed/timeout entries actually
being logged.

**Choosing the right `--outcome`:**

| Outcome       | When                                                                    | Counts toward circuit breaker? |
| ------------- | ------------------------------------------------------------------------ | ------------------------------- |
| `success`     | DoD passed, stage handed off                                            | resets the count                |
| `fail`        | A real DoR/DoD criterion wasn't met — a genuine quality gap              | yes                              |
| `timeout`     | A previous attempt hung past its time budget (see the `stage-timeout` label handling in `on-start-checks.skill.md`) | yes |
| `infra_error` | A transient, non-quality problem (rate limit, network blip, a tool briefly unavailable) kept you from completing the check at all | no |

Getting this classification right matters: `infra_error` exists specifically so a GitHub API
hiccup doesn't burn one of the 3 retry slots meant for real quality problems. When in doubt — could
a human have hit the exact same wall through no fault of the work itself? — log `infra_error`, not
`fail`.

**Optional: `--tokens-input` / `--tokens-output`.** If — and only if — your own runtime exposes
your session's token usage to you, pass it along; this feeds the token columns in
`.orchestrator/docs/ops/telemetry-rollup.md` (see `telemetry-rollup.py`), giving a rough per-stage cost signal
over time. Most runs won't have this available — omit the flags entirely rather than guessing or
estimating a number. An absent value is treated as "not reported," never as zero.

## Posting the comment

Use the "Completion" (or "Reviewer FAIL", if applicable) template from
[`ticket-comments.skill.md`](ticket-comments.skill.md). Post it **after** the commit and board
update, so the comment's links resolve to content that's actually there.
