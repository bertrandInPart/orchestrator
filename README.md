# orchestrator

**orchestrator** is a template/toolkit for running an *agentic feature production chain* on top
of GitHub Copilot. It turns "build a feature" into a fixed pipeline of specialized Copilot chat
modes — spec-writer → architect → backend-builder / frontend-builder → test-engineer → reviewer →
release-engineer — each with its own instructions, write-path boundaries, and definition of
ready/done, coordinated end-to-end through a single GitHub Issue plus a GitHub Projects (v2) board
(Jira is also supported as an alternative ticket backend).

It ships as a **package you install into an existing repository** (via `.orchestrator/scripts/install.py`),
not something you build on top of directly. The chain logic, docs, scripts, and eval harness live
almost entirely under `.orchestrator/`; only the handful of files GitHub/Copilot require at fixed
paths (chat modes, instructions, prompts, issue templates, workflows) live under `.github/`.

A small local dashboard (`.orchestrator/dashboard/`) is included to visualize where every feature
sits in the chain.

## How the chain works

```
spec-writer → architect → backend-builder ─┐
                                            ├→ test-engineer → reviewer → release-engineer
                            frontend-builder┘
```

- **spec-writer** — always started by a human, interactively. Runs an interrogation pass (scope,
  edge cases, UX, non-functional concerns), then files the GitHub issue itself and writes `spec.md`.
- **architect** — turns an approved spec into `architecture.md` (contracts, schema, task breakdown).
- **backend-builder** / **frontend-builder** — implement against the architecture, in parallel,
  restricted to `server/**` / `client/**` respectively.
- **test-engineer** — writes/runs tests against the acceptance criteria.
- **reviewer** — governance pass (PII, secrets, auth boundaries, migration safety, dependency risk,
  path boundaries) — advisory, not a merge gate.
- **release-engineer** — opens the PR (`Closes #<issue>`), so merging carries the ticket to `Done`.

Every feature's state lives in three places that must never disagree: a comment thread on the
GitHub Issue, custom fields (`Stage`, `Current Agent`, `Feature Slug`, `Feature Branch`) on the
Projects v2 board, and a per-feature **lifecycle file** under
`.orchestrator/docs/features/<slug>/` — the lifecycle file is the source of truth; the board and
comments mirror it. Stage-to-stage handoff (other than spec-writer) is dispatched automatically by
scheduled Copilot workflows polling the board every 15 minutes — see
`.orchestrator/automations/README.md` for exactly what's configured. `Spec Review` and
`Architecture Review` are deliberate human checkpoints: re-assigning the issue is both the approval
and the trigger for the next automation.

## Repository layout

```
.github/
  chatmodes/        one file per agent role (spec-writer, architect, backend-builder, ...)
  instructions/     shared + stack-scoped instructions (applyTo: frontmatter scopes each one)
  prompts/          entry points, e.g. new-feature.prompt.md, audit-spec.prompt.md
  ISSUE_TEMPLATE/   feature-request.yml — the intake form spec-writer files through the API
  workflows/        CI, deploy, project-board automation (GitHub Actions)
  copilot-instructions.md   always-loaded, repo-wide Copilot context

.orchestrator/
  README.md         packaging/layout details for this folder
  VERSION            semver of this package
  CHANGELOG.md       what changed release to release
  manifest.yml       full packaged file list (core / integration / seed), read by install.py
  agent-boundaries.yml  enforced per-agent write-path allow-list
  config.yml         project-specific settings written by init-wizard.py
  automations/       record of the scheduled Copilot workflows that dispatch each stage
  docs/
    features/<slug>/  per-feature spec/architecture/notes/test-plan/review-notes/lifecycle
    memory/           durable cross-feature context (conventions, past decisions) — append-only
    ops/              telemetry log, pause switch (CHAIN_PAUSED), bot-identity notes
    jira-integration.md
  evals/              regression harness for the chain's own chatmodes (not the product being built)
  scripts/            install.py, init-wizard.py, boundary/DoR/DoD checks, telemetry, board setup
  skills/             shared step-by-step procedures every chatmode references
  dashboard/          local Node/Express + React/Vite app that visualizes the board + lifecycles

server/, client/      the actual product code once a feature chain starts producing it
                      (Node/Express backend, Angular frontend, MongoDB Atlas/Mongoose — see
                      .github/copilot-instructions.md for the current stack)
```

## Installation

There are two things to install, depending on what you're doing:

### 1. Adopt the chain into your own project

From the root of the project you want to add the agentic chain to:

```powershell
python /path/to/orchestrator/.orchestrator/scripts/install.py --source /path/to/orchestrator
# or install straight from GitHub at a pinned version:
python -c "$(curl -fsSL https://raw.githubusercontent.com/<OWNER>/<REPO>/v0.2.0/.orchestrator/scripts/install.py)" -- --ref v0.2.0
```

This is safe to run against a project that already has its own CI, `copilot-instructions.md`, or
issue templates — it never silently overwrites a file that already exists and differs from the
incoming version. Instead it writes the incoming version alongside as
`<name>.orchestrator-suggested<ext>` and lists every such conflict, flagging `integration`-category
files (CI workflows, repo-wide Copilot instructions, the issue template) as needing a manual
merge. Run with `--dry-run` first to preview. Re-run later with `--update` to pull a newer version.

Then adapt it to your project:

```powershell
python .orchestrator/scripts/init-wizard.py
```

This detects your language/framework/paths, asks you to confirm or override its guesses, asks
whether ticket tracking is GitHub Issues + Projects or Jira, collects a few more first-run
parameters (enabled stages, human-checkpoint stages, circuit-breaker threshold, deploy targets, bot
commit identity), and rewrites the chatmodes/instructions/`agent-boundaries.yml` accordingly,
recording every decision in `.orchestrator/config.yml`.

### 2. Set up this repository itself for local development

Requirements: **Node.js 18+**, **Python 3** (for the scripts), **git**, and the **GitHub CLI**
(`gh`, authenticated) if you'll be interacting with the Projects v2 board.

```powershell
git clone https://github.com/<OWNER>/<REPO>.git
cd orchestrator
```

If the ticket-tracking board hasn't been created yet, a human runs (once):

```powershell
bash .orchestrator/scripts/setup-github-project.sh
```

then records the resulting `PROJECT_OWNER` / `PROJECT_NUMBER` in
`.github/instructions/github-workflow.instructions.md`.

## Usage

### Starting a new feature

Spec-writer is the only stage a human starts directly — never an automation. In Copilot Chat, run
the prompt:

```
/new-feature
```

(`.github/prompts/new-feature.prompt.md`), or switch to the `spec-writer` chat mode yourself, and
describe the feature. Spec-writer interrogates you on scope, edge cases, UX, and non-functional
concerns; only once you're both satisfied does it file the GitHub issue (from
`.github/ISSUE_TEMPLATE/feature-request.yml`, via the API), create the `feature/<slug>` branch,
and write `spec.md`. From there, `Stage: Spec Review` — approve by re-assigning the issue, and the
scheduled automations carry it through architecture, implementation, testing, review, and release
without further manual dispatch, pausing only at the two human checkpoints (`Spec Review`,
`Architecture Review`).

To audit the scope of an **existing** issue without drafting a new one, use:

```
/audit-spec
```

(`.github/chatmodes/spec-auditor.chatmode.md`) — it appends a `## Scope Review` section to the
issue and never touches `Stage`/`Current Agent`.

To pause the whole chain, create `.orchestrator/docs/ops/CHAIN_PAUSED` — every agent checks for it
before doing anything and stops immediately if it's present. Delete the file to resume.

### Running the workflow dashboard

A local read-only visualization of the board and per-feature lifecycle history:

```powershell
cd .orchestrator\dashboard
npm install
$env:GITHUB_TOKEN = "<token with repo + read:project scope>"   # or $env:JIRA_EMAIL / $env:JIRA_API_TOKEN
npm run dev
```

Open `http://localhost:5173` (API on `http://localhost:4000`, override with `$env:DASHBOARD_PORT`).
For a single-process production-style run: `npm start`. See
`.orchestrator/dashboard/README.md` for the API surface and details.

### Running the chain's own eval harness

```powershell
bash .orchestrator/scripts/run-agent-evals.sh <agent-name>
```

Grades each agent's chatmode against its cases/rubric under `.orchestrator/evals/<agent>/`; see
`.orchestrator/evals/README.md`. CI's `eval-gate` job requires fresh eval evidence for any PR that
touches a chatmode or shared skill/instructions file.

## Governance & CI enforcement

- **Agent boundaries** — `.orchestrator/scripts/check-agent-boundaries.sh` fails CI if a commit
  touches a path outside the acting agent's `allowed_write_paths` (declared per chat mode,
  enforced against `.orchestrator/agent-boundaries.yml`).
- **Security & data rules** — PII handling, secrets, auth boundaries, migration safety, and
  dependency risk are checked every run by the reviewer stage; see
  `.github/instructions/security.instructions.md`. A reviewer PASS is advisory context for the
  human merging the PR, not the merge gate itself — CI (lint, tests, secret-scan, boundary check)
  is.
- **Commits** — every commit must carry an `Agent: <name>` trailer; commits without one fail CI.

## Versioning

`.orchestrator/VERSION` holds this package's semver; `.orchestrator/CHANGELOG.md` records what
changed release to release. Pin an install to a specific release with `install.py --ref vX.Y.Z`.

## Further reading

- `.orchestrator/README.md` — packaging/layout rationale for the `.orchestrator/` folder.
- `.github/instructions/github-workflow.instructions.md` — the ticket/board model in full.
- `.orchestrator/docs/jira-integration.md` — using an existing Jira project instead of GitHub Projects.
- `.orchestrator/automations/README.md` — the scheduled Copilot workflows that dispatch each stage.
- `.orchestrator/docs/memory/decisions.memory.md` — durable design rationale and past decisions.
