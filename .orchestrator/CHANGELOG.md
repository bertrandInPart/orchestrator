# Changelog

All notable changes to the orchestrator package itself (not to any project that adopts it) are
recorded here. Versions are plain semver; `install.py --ref vX.Y.Z` pins an adopting project to a
specific one.

## 0.2.0 — 2026-07-17

- Redesigned the Jira ticket-system integration to adopt an **existing** Jira project's own
  workflow instead of requiring new custom fields or admin access: `Stage` now moves the issue's
  native `status` via workflow transitions (looked up through a new, human-supplied
  `ticket_system.jira.stage_status_map` in `.orchestrator/config.yml`), `Current Agent` is tracked
  as an `agent:<name>` label instead of `assignee`, and `Feature Slug`/`Feature Branch` default to
  the issue key/a naming convention instead of dedicated custom fields (with an opt-out via
  `JIRA_FEATURE_SLUG_FIELD`/`JIRA_FEATURE_BRANCH_FIELD` for projects that already track those).
- `setup-jira-project.sh` is now a read-only validation script (was: field-creation script
  requiring Jira admin permissions) — it checks `stage_status_map` against the project's real
  statuses instead of creating anything.
- `update-jira-ticket.sh` now fires workflow transitions for `Stage` and manages the `agent:*`
  label for `Current Agent`, instead of writing to custom fields that no longer exist.
- `init-wizard.py`'s Jira setup flow now collects `stage_status_map` interactively.
- The dashboard's Jira adapter (`dashboard/server/adapters/jira.js`) now reads `currentAgent` from
  the `agent:*` label, matching the write side, instead of from `assignee`.
- Added `.orchestrator/docs/jira-integration.md` documenting the full design and a JQL-equivalent
  table for the polling automations described in `.orchestrator/automations/README.md`.

## 0.1.0 — 2026-07-13

- First packaged version. Adds `.orchestrator/manifest.yml`, `.orchestrator/scripts/install.py`,
  and `.orchestrator/scripts/init-wizard.py` so the chain can be installed non-destructively into
  an existing ("already industrialized") project and then adapted to that project's own
  language/framework/paths and GitHub-vs-Jira ticket tracking.
- Everything prior to this (chatmodes, skills, instructions, evals, GitHub workflows/scripts) is
  the chain itself, unversioned before this point.
