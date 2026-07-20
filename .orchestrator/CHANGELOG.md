# Changelog

All notable changes to the orchestrator package itself (not to any project that adopts it) are
recorded here. Versions are plain semver; `install.py --ref vX.Y.Z` pins an adopting project to a
specific one.

## 0.3.0 — 2026-07-19

- **Path literals in the shared chatmodes/instructions/skills/`agent-boundaries.yml` are now
  generic placeholders** (`{{backend.path}}`, `{{frontend.path}}`, `{{migrations.path}}`) instead
  of the template's own `server/**`/`client/**`/`migrations/**` example baked directly into prose.
  This is the prerequisite for vendoring this repo as a shared **git submodule** across multiple
  consuming repos (e.g. separate backend/frontend repos for the same product) instead of each one
  carrying its own drifted copy: the same file content is now valid for any consuming project
  regardless of its actual directory layout, because the paths are resolved from that project's
  own `.orchestrator/config.yml` rather than being rewritten into the file text.
  - `check-agent-boundaries.sh` now resolves `agent-boundaries.yml`'s placeholders against
    `.orchestrator/config.yml` (`backend.path`/`frontend.path`/`database.migrations_path`) at
    check time, including safe handling of a repo-root path (config value `"."`, e.g. a
    backend-only repo where the whole repo *is* the backend) and of a disabled/not-applicable side
    of the stack (which now resolves to a pattern that can never match, instead of literally
    matching `client/**`/`N/A/**` as before).
  - `applyTo:` frontmatter in `.github/instructions/*.instructions.md` and the three
    `.github/workflows/*.yml` deploy/CI placeholders are the only remaining literal-path spots —
    `applyTo` is matched natively by Copilot's own instructions-attachment engine (no templating
    hook available there), and the workflow files only ever referenced paths in comments/TODOs.
    `init-wizard.py`'s existing one-shot literal substitution still covers exactly those spots;
    everywhere else needed no further changes since the paths are no longer literal text to rewrite.
- Fixed a latent bug this surfaced: a repo where `backend.path` is `"."` (the repo root) previously
  got a boundary of `./**`, which `check-agent-boundaries.sh`'s glob matching never actually
  matched against any real file — i.e. `backend-builder` had no effectively-enforced write access
  at all in that configuration. `./` now normalizes to the repo root correctly.

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
