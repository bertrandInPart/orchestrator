# Adapting the chain to an existing Jira project

This document is the design rationale behind `ticket_system.provider: jira`. If you just need the
day-to-day field reference, read `.github/instructions/jira-workflow.instructions.md` (generated
for your project by the wizard) instead — this file explains *why* it's shaped that way, so a
human reviewing or debugging the integration understands the constraints it was built under.

## The constraint this is built around

Most teams adopting this chain into a codebase that already has its own Jira project do **not**
want (and often cannot get, without a separate admin conversation) four new custom fields added to
that project's screens, nor do they want their existing workflow's statuses duplicated by a
parallel "Stage" field. The chain has to sit *inside* whatever workflow already exists, not next to
it. Concretely, that means:

- No new custom fields are created. `.orchestrator/scripts/setup-jira-project.sh` is read-only —
  it validates your configuration against Jira, it never writes to Jira.
- No Jira admin permission is required for a human to complete setup — only the same
  create-issue/comment/transition-issue permissions any project contributor already has.
- The chain has to tolerate workflows with far fewer than 11 statuses (many teams run a 3- or
  4-status workflow: `To Do` / `In Progress` / `In Review` / `Done`), since the chain has 11
  stages (`Backlog` through `Done`) but nothing requires a 1:1 status-per-stage mapping.

## Field mapping

| Chain concept | Backing Jira field | Why this field |
|---|---|---|
| `Stage` | native issue `status`, moved via workflow transitions | Every Jira project already has a status field with real, in-use transitions — reusing it (instead of a parallel custom "Stage" field) is what makes this an *adoption* rather than a schema addition. |
| `Current Agent` | native issue `labels`, as `agent:<name>` | Labels exist on every Jira project without any setup, are cheap to add/remove per API call, and don't collide with `status`, which is reserved for `Stage`. Using `assignee` for this was considered and rejected — `assignee` already carries a real meaning (which human/bot Jira account owns the issue) that's orthogonal to "which chain stage is next," and repurposing it would break normal Jira reporting for a team that also uses assignee for its own purposes. |
| `Feature Slug` | the issue key itself (e.g. `FEAT-123`, lowercased) | The issue key is already a stable, unique, human-readable identifier — introducing a second one is redundant. Opt out via `JIRA_FEATURE_SLUG_FIELD` if your project already tracks something like this. |
| `Feature Branch` | not stored — computed as `feature/<issue-key-lowercased>` | A convention every agent (and any human) can derive independently, with nothing to keep in sync. Opt out via `JIRA_FEATURE_BRANCH_FIELD`. |
| `blocked` / other flags | native issue `labels` | Same reasoning as `Current Agent` — no pre-creation needed, unlike GitHub repo labels. |

This is deliberately the same shape the dashboard's read-only adapter
(`.orchestrator/dashboard/server/adapters/jira.js`) already assumed for `status`/`labels` before
the write side (`update-jira-ticket.sh`) was brought in line with it — see
`.orchestrator/CHANGELOG.md` for when that alignment happened.

## `stage_status_map`

Because a real project's workflow rarely has exactly 11 statuses, `.orchestrator/config.yml`
records an explicit mapping from every chain stage to one of *your* project's real status names:

```yaml
ticket_system:
  provider: "jira"
  jira:
    base_url: "https://your-domain.atlassian.net"
    project_key: "FEAT"
    stage_status_map:
      Backlog: "To Do"
      Spec Drafting: "In Progress"
      Spec Review: "In Review"
      Architecture Drafting: "In Progress"
      Architecture Review: "In Review"
      Implementation: "In Progress"
      Testing: "In Progress"
      Governance Review: "In Review"
      Release Prep: "In Progress"
      PR Open: "In Review"
      Done: "Done"
```

Multiple chain stages mapping to the same status (as in the example above) is expected and
correct — the chain still knows exactly which stage a feature is in via the lifecycle file
(`.orchestrator/docs/features/<slug>/*_lifecycle.md`, the actual source of truth) and the
`agent:<name>` label; the Jira status only needs to be coarse enough to reflect real workflow
progress to anyone glancing at the Jira board, not to enumerate all 11 stages 1:1.

`init-wizard.py` asks for this mapping interactively (with the 4-status example above as the
default) when you choose `jira` as the ticket provider. Run
`.orchestrator/scripts/setup-jira-project.sh <PROJECT_KEY>` any time afterward — including
whenever someone edits the real workflow in Jira later — to re-validate every entry against the
project's actual statuses.

## How `update-jira-ticket.sh` moves `Stage`

1. Look up the target chain stage in `stage_status_map` to get a target status name.
2. Call `GET /rest/api/3/issue/{key}/transitions` to list the transitions *actually available*
   from the issue's current status (Jira only exposes the transitions reachable in one hop, same
   as the workflow diagram would show).
3. Find the transition whose `to.name` matches the target status name and fire it via
   `POST /rest/api/3/issue/{key}/transitions`.
4. If no such transition exists — e.g. the mapped status isn't reachable in one hop from wherever
   the issue currently sits — the script fails loudly and prints the transitions that *are*
   available, rather than silently skipping the move or guessing a workaround.

That last point is a real limitation worth knowing about: workflows with restrictive transition
graphs (e.g. no direct `To Do -> Done` transition) can reject a stage move that skips statuses.
This is treated as a signal to fix `stage_status_map` (map more chain stages onto the same,
always-reachable status) rather than something the chain works around by chaining transitions
automatically — an agent silently hopping through several status changes on your team's behalf is
a bigger surprise than a clear error.

## Automations: the one thing this can't paper over

`.orchestrator/automations/README.md` documents 6 stage-dispatch automations, each a scheduled
Copilot workflow polling GitHub Projects v2 for a `Stage`/`Current Agent` field combination. Their
JQL equivalent against Jira is:

| Automation | JQL |
|---|---|
| Architect | `project = <KEY> AND status = "<stage_status_map['Architecture Drafting']>" AND labels = "agent:architect"` |
| Backend/Frontend Builder | `project = <KEY> AND status = "<stage_status_map['Implementation']>" AND (labels = "agent:backend-builder" OR labels = "agent:frontend-builder")` |
| Test Engineer | `project = <KEY> AND status = "<stage_status_map['Testing']>" AND labels = "agent:test-engineer"` |
| Reviewer | `project = <KEY> AND status = "<stage_status_map['Governance Review']>" AND labels = "agent:reviewer"` |
| Release Engineer | `project = <KEY> AND status = "<stage_status_map['Release Prep']>" AND labels = "agent:release-engineer"` |

Substitute your project's real `stage_status_map` values for the placeholders above.

The one thing that doesn't carry over automatically: the Copilot app's scheduled-workflow system
dispatches against **this repo's** GitHub state, not Jira's. There is no equivalent built-in
cron-poller that watches a JQL filter and starts a chatmode session. Until/unless a workflow is
pointed at Jira directly, the practical options are:

1. A human periodically (or on a Jira automation rule triggered by the status/label change above)
   starts the next chatmode manually, pointed at the issue key.
2. An external scheduler (e.g. a lightweight cron job or a Jira Automation "webhook" rule) calls
   out to trigger the appropriate Copilot session — outside the scope of what this package ships,
   since it depends on how your org runs Copilot outside of GitHub Actions.

Everything else in the chain — the chatmodes, the skills, the DoR/DoD criteria, the lifecycle
file, the commit trailers — is provider-agnostic and works identically either way.

## Setup checklist

1. Run `.orchestrator/scripts/init-wizard.py`, choose `jira` as the ticket provider, and answer
   the `stage_status_map` prompts with your project's real status names.
2. Set `JIRA_EMAIL` and `JIRA_API_TOKEN` as environment variables/secrets wherever agents run (see
   `.orchestrator/docs/ops/bot-identity.md`) — never commit them.
3. Run `.orchestrator/scripts/setup-jira-project.sh <PROJECT_KEY>` to validate the mapping
   read-only against your real project.
4. (Optional) If your project already has fields you'd rather use for feature slug/branch instead
   of the issue-key convention, set `JIRA_FEATURE_SLUG_FIELD` / `JIRA_FEATURE_BRANCH_FIELD` to
   their custom field IDs (e.g. `customfield_10050`) as env vars.
5. Read the generated `.github/instructions/jira-workflow.instructions.md` end to end before the
   first feature enters the chain.
