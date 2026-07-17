# Bot identity & credentials

Per blueprint §11, unattended workflows (`add-to-project.yml`, `chain-health.yml`) and the
one-time `setup-github-project.sh` need a non-human identity so revoking access and reading audit
logs doesn't depend on tracking down "whose personal token was this."

## Current setup (deliberate simplification for a solo-maintained repo)

This repo has a single maintainer, so we are **not** using a dedicated GitHub App
right now. Instead:

- **Actions inside a Copilot cloud agent automation** (issue comments, commits, PR creation, board
  field edits made by the chatmode agents themselves) run under GitHub's built-in Copilot bot
  actor for things routed through Copilot's own tools (file edits, its own commit/PR creation).
  **This does *not* cover raw `gh` CLI calls made from inside a chatmode's own shell** — several
  skills and scripts (`.orchestrator/scripts/update-ticket-stage.sh`'s `gh project ...` calls in particular, since
  Projects v2 needs the `project` scope the default cloud-agent credential doesn't carry — the
  same gotcha noted below for `GITHUB_TOKEN`) run plain `gh`, which needs its own authenticated
  token in that shell. That token is supplied via a repository secret named **`GH_TOKEN`** in the
  special **`copilot`** GitHub Environment (Settings → Environments → `copilot` → Environment
  secrets) — the mechanism GitHub documents for injecting environment variables into a Copilot
  cloud agent's session. `gh` auto-detects `GH_TOKEN` with no extra configuration needed in any
  chatmode or script. Currently holds the maintainer's own PAT (same value as `CHAIN_BOT_TOKEN`
  below, since this is still a solo-maintained repo — see the upgrade path if that changes).
- **Actions outside that sandbox** — `add-to-project.yml`, `chain-health.yml`, and the one-time
  `.orchestrator/scripts/setup-github-project.sh` — use the maintainer's own personal access token, stored as
  the repository secret **`CHAIN_BOT_TOKEN`**. This token is never committed, never printed in a
  log, and never passed as a bare script argument.
- `.orchestrator/scripts/setup-github-project.sh` was run once, directly under the maintainer's own `gh auth`
  session (not via the secret) — consistent with blueprint §11.4's guidance to keep that
  one-time, human-run action tied to a person, not the system identity.

## Why this is a documented deviation, not an oversight

The blueprint's GitHub App recommendation (§11.2) is about least-privilege and clean audit trails
once **multiple people** can push to or administer the repo — a solo maintainer's own PAT already
is the actual human accountable for those actions, so a separate bot identity doesn't add
isolation it doesn't already have.

## Upgrade path (do this if collaborators are added)

1. Create a narrowly-scoped GitHub App (e.g. `feature-chain-automation`), installed only on this
   repo, granted only: Issues (read/write), Pull requests (read/write), Projects (read/write),
   Contents (read-only).
2. Store its App ID and private key as repository secrets (`CHAIN_BOT_APP_ID`,
   `CHAIN_BOT_PRIVATE_KEY`).
3. Update `add-to-project.yml` and `chain-health.yml` to exchange those for a short-lived
   installation token at the start of the job (via `actions/create-github-app-token` or
   equivalent) instead of `CHAIN_BOT_TOKEN`.
4. Revoke `CHAIN_BOT_TOKEN` once the App-based workflows are confirmed working.

## A concrete gotcha, confirmed against this repo

The default `GITHUB_TOKEN` Actions provides does **not** carry Projects v2 access — this is why
`add-to-project.yml` and `chain-health.yml` explicitly use `CHAIN_BOT_TOKEN` rather than the
default token. The same gap showed up a second time in the Copilot cloud agent's own session
shell (not GitHub Actions): a bare `gh` call there had no authenticated token at all until the
`GH_TOKEN` secret was added to the `copilot` Environment (see above) — before that, agents got a
plain `404 Not Found` from `gh api`/`gh project ...`, which looks like a missing-repo error but
was actually a missing-credential error against this private repo.

## What must never happen

- The token's value must never appear in a commit, workflow YAML (only the secret *name* may
  appear), or a script argument.
- Same rule for the `copilot` Environment's `GH_TOKEN` secret: never printed, never echoed by a
  chatmode into a ticket comment, never passed as a bare CLI argument (only `gh`'s own
  auto-detection of the `GH_TOKEN` environment variable may consume it).
- `.orchestrator/scripts/check-agent-boundaries.sh`'s boundary check treats any commit touching this file as
  worth a closer look (it's in every agent's effective "sensitive path" set via review — see
  `security.instructions.md`), since it documents (not contains) credential handling.
