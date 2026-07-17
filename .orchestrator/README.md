# .orchestrator/

## Adopting this into a project

This is packaged as an installable unit, not just something you clone the whole repo for. See
`.orchestrator/manifest.yml` (the full file list, tagged `core`/`integration`/`seed`),
`.orchestrator/VERSION`, and `.orchestrator/CHANGELOG.md`.

**1. Install.** From the root of the project you're adopting the chain into:

```bash
python /path/to/orchestrator/.orchestrator/scripts/install.py --source /path/to/orchestrator
# or, installing straight from GitHub at a pinned version:
python -c "$(curl -fsSL https://raw.githubusercontent.com/<OWNER>/<REPO>/v0.1.0/.orchestrator/scripts/install.py)" -- --ref v0.1.0
```

This is safe to run against an **already-industrialized project** — one with its own CI, its own
`.github/copilot-instructions.md`, its own issue templates. It never overwrites a file that
already exists and differs from the incoming version; instead it writes the incoming version
alongside as `<name>.orchestrator-suggested<ext>` and lists every such conflict at the end,
calling out `integration`-category files (CI workflows, repo-wide Copilot instructions, the issue
template) as needing a manual merge rather than a drop-in replacement. Run `--dry-run` first if
you want to see what it would do before it writes anything. Re-run later with `--update` to pull a
newer version — anything you haven't modified since install is refreshed automatically; anything
you have is left alone and flagged as a conflict, same as a fresh install.

**2. Adapt.** Run `python .orchestrator/scripts/init-wizard.py` next. It analyzes the project's
language/framework/paths, asks you to confirm or override its guesses, asks whether ticket
tracking runs on GitHub Issues + Projects or Jira, and a short list of other first-run parameters
(which chain stages to enable, human-checkpoint stages, circuit-breaker threshold, deploy targets,
bot commit identity) — then rewrites the paths/stack-vocabulary baked into the chatmodes,
instructions, and `agent-boundaries.yml` accordingly, and records every decision in
`.orchestrator/config.yml`. See the script's own docstring for exactly what it does and does not
automate. **If you choose Jira**, this adopts your project's *existing* workflow as-is — no new
custom fields, no admin permissions required — see `.orchestrator/docs/jira-integration.md` for
exactly how chain state maps onto fields your Jira project already has.

Everything the agentic feature-production chain needs to operate, in one place, **except** the
handful of files GitHub and Copilot require to live at fixed paths for their own tooling to find
them. Those stay under `.github/` (see "What's not here, and why" below) — moving them would
silently break discovery, not just relocate a file.

## Layout

```
.orchestrator/
  VERSION                # semver of this package; installed copies record their ref in INSTALLED.json
  CHANGELOG.md           # what changed release to release
  manifest.yml           # full packaged file list, tagged core/integration/seed for install.py
  agent-boundaries.yml   # enforced allow-list per agent, checked by scripts/check-agent-boundaries.sh
  automations/           # README documenting the 7 stage-dispatch automations + the eval-sweep
  docs/
    features/<slug>/     # per-feature spec/architecture/notes/lifecycle (created as features run)
    memory/              # durable cross-feature context: conventions, past decisions (append-only)
    ops/                 # telemetry log, pause switch (CHAIN_PAUSED), bot-identity notes
    jira-integration.md  # design rationale for adopting an EXISTING Jira project/workflow —
                          # see this before touching anything Jira-related in this package
  evals/                 # regression harness for the chain's own chatmodes (not the app being built)
    <agent>/rubric.yml + cases/
    results/             # graded evidence, evals/README.md explains how it's produced
  scripts/               # the shell/python mechanics: boundary checks, DoR/DoD helpers,
                          # telemetry logging/rollup, eval freshness gate, project-board setup,
                          # install.py (packaging) and init-wizard.py (stack/ticket-system adapt)
  skills/                # shared step-by-step procedures every chatmode references (DoR/DoD
                          # checks, ticket-comment templates, lifecycle file, commit/handoff,
                          # context scope) — factored once here instead of duplicated per chatmode
```

## What's not here, and why

| Path | Stays because |
|---|---|
| `.github/workflows/**` | GitHub Actions only ever reads workflow definitions from this exact path. |
| `.github/ISSUE_TEMPLATE/**` | GitHub only reads issue-form templates from this exact path. |
| `.github/chatmodes/**` | Copilot's custom chat mode discovery in VS Code/Copilot Chat looks here specifically. |
| `.github/instructions/**` | Copilot's `applyTo`-based auto-loading of instructions looks here specifically. |
| `.github/prompts/**` | Copilot's workspace prompt-file discovery looks here specifically. |
| `.github/copilot-instructions.md` | The one always-loaded, repo-wide instructions file — fixed path. |

Every one of those files links out to `.orchestrator/skills/**`, `.orchestrator/docs/**`, etc. for
the actual mechanics — they're deliberately thin pointers into this folder, not a second copy of
its content.

## If you're an agent reading this

Start from your own `.github/chatmodes/<you>.chatmode.md` — it links to exactly the
`.orchestrator/skills/*.skill.md` files you need, per `.orchestrator/skills/context-scope.skill.md`'s
"read only what you need" rule. This file is orientation for a human (or a first-time reader),
not another thing to load into every agent run.
