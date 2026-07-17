# Skill: On-start checks

Every agent runs this exact sequence first, before anything stage-specific, on every single run
— whether triggered by a scheduled workflow or started by a human. None of these steps are
optional, and none of them require judgment; if any check fails, follow its stop instruction and
do not proceed to your stage-specific work.

1. **Pause switch.** Check whether `.orchestrator/docs/ops/CHAIN_PAUSED` exists on the feature branch (or
   `develop` if no feature branch is checked out yet). If it exists: stop immediately. Do not
   read further, do not comment, do not touch the board. This overrides everything else, in this
   file and in your own chatmode.
2. **Circuit breaker.** Count trailing `fail`/`timeout` entries for this issue + your stage in
   `.orchestrator/docs/ops/agent-telemetry.jsonl` since the last `success`. If the count has reached 3: do not
   attempt the stage. Set `Current Agent` to `none`, add the `blocked` label (create it first if
   missing — see the idempotent `gh label create` step in `ticket-comments.skill.md`'s Escalation
   template), post a comment summarizing the failure history and tagging a human, and stop.
   **`infra_error` entries never count toward this** — they mean a transient problem (rate limit,
   network blip, a tool that was briefly unavailable), not a real quality issue, and shouldn't burn
   a retry slot meant for genuine DoR/DoD failures. If your own run fails for a clearly transient,
   non-quality reason, log `infra_error` (see `commit-and-handoff.skill.md`) and stop quietly —
   don't post a callback/escalation comment, since nothing about the work itself was wrong. The
   next scheduled tick will simply retry.
3. **Stage-timeout label.** If the issue carries a `stage-timeout` label, your previous attempt at
   this stage hung past its time budget (a watchdog in `chain-health.yml` applies this label — see
   its "Scan for hung stage attempts" step). Before doing anything else: log that previous attempt
   as outcome `timeout` in `.orchestrator/docs/ops/agent-telemetry.jsonl`, using the timestamp from your last
   "starting work" comment as `--started-at` and incrementing `--attempt`, then remove the
   `stage-timeout` label. This is what lets a hang actually count toward the circuit breaker in
   step 2, instead of vanishing silently. Then continue normally — the hang doesn't block this new
   attempt, it just needs to be on the record.
4. **Idempotency check.** If your stage's output file already exists under `.orchestrator/docs/features/<slug>/`
   **and** `Stage` is already at or past the value your stage produces, this is a duplicate
   trigger (a retried automation run, a duplicate event). Do nothing further and exit — don't
   re-write files, don't re-post a comment, don't re-move `Stage`.
5. Resolve the issue number, `Feature Slug`, and `Feature Branch` for this feature from the
   Projects v2 board.
6. Check out `Feature Branch` exactly as recorded on the board — never a new or default branch.
   (Exception: Spec Writer, before the branch exists yet — see `spec-writer.chatmode.md`.)
7. Read the issue body and every comment added since your own last comment (or since the last
   agent's comment, if this is your first run on this issue). A human may have left clarification
   directly on the issue rather than waiting to be asked again — don't proceed on stale
   assumptions if so.
8. Confirm `Current Agent` matches your agent name. If it doesn't, and the stage isn't a
   human-review checkpoint the human has just released, stop and flag the mismatch rather than
   proceeding — this usually means the wrong agent was invoked or a previous handoff didn't
   complete cleanly.

Only once all eight checks pass do you move on to your DoR check (see
[`dor-check.skill.md`](dor-check.skill.md)) and then your stage-specific mandate.
