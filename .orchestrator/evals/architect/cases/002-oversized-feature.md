# Case 002 — Feature too large for one session

## Input

`.orchestrator/docs/features/full-project-dashboard/spec.md` (approved): a large feature spec describing a new
project dashboard with six independent widgets (activity feed, task burndown chart, team
workload heatmap, budget tracker, file activity, and a notifications panel), each pulling from a
different existing collection, with real-time updates via polling.

## Answer key — a good architecture.md for this case must

- Explicitly state that this is too large for Backend Builder or Frontend Builder to implement in
  a single cloud agent session (per the session-length constraint), rather than writing one giant
  undifferentiated plan and letting a later stage silently time out.
- Propose a concrete split into sequential sub-tasks (e.g. one widget or a small group of related
  widgets per sub-task), each sized to fit one session.
- Still freeze the overall API contract/shape for at least the first sub-task's widgets so
  Backend/Frontend Builder aren't blocked waiting on a second architecture pass for the first
  chunk of work.
- NOT simply ignore the sizing problem and produce a single unified plan with no acknowledgment
  that it's large.
