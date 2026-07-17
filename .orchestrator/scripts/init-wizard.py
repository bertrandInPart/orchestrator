#!/usr/bin/env python3
"""
init-wizard.py — Startup wizard for adopting `.orchestrator` in a new project.

Run this ONCE, by a human, right after copying this template into a fresh
repository, from that repository's root:

    python .orchestrator/scripts/init-wizard.py

What it does, in order:
  1. Analyzes the current working directory to guess the project's languages,
     frameworks, backend/frontend paths, database/ORM, and test conventions.
  2. Shows you what it found and lets you confirm or override every value.
  3. Asks whether ticket/project management runs on GitHub Issues + Projects
     (the default this template ships with) or Jira, and collects the
     provider-specific values it needs.
  4. Asks a short list of additional first-run parameters (which chain stages
     you want, which stages need a human checkpoint, the circuit-breaker
     threshold, deploy targets, bot/commit identity).
  5. Writes `.orchestrator/config.yml` recording every decision.
  6. Rewrites the path- and stack-specific literals baked into the chatmodes,
     instructions, and agent-boundaries.yml so they match your project instead
     of this template's original Node/Express/Angular/MongoDB/GitHub example.
  7. If you chose Jira, swaps the GitHub-flavored ticket-workflow instructions
     and scripts for Jira equivalents.

This is a one-shot templating pass, not an idempotent generator — it edits the
checked-in files in place. Re-running it is safe but will re-apply
replacements against whatever the files currently say, not against the
original template, so review the diff before committing.

Limitations (deliberately out of scope for this pass — see the summary this
script prints at the end): the `.orchestrator/evals/**` case files and
GitHub's `ISSUE_TEMPLATE/feature-request.yml` still reference the template's
original example stack/ticket system and are not rewritten automatically;
review them by hand if they matter to you.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
).stdout.strip() or os.getcwd())

GITHUB_DIR = REPO_ROOT / ".github"
ORCH_DIR = REPO_ROOT / ".orchestrator"


# --------------------------------------------------------------------------
# Small prompt helpers
# --------------------------------------------------------------------------

def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_label = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{default_label}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer y or n.")


def ask_choice(prompt: str, choices: list[str], default: str) -> str:
    choice_str = "/".join(c if c != default else c.upper() for c in choices)
    while True:
        raw = input(f"{prompt} ({choice_str}): ").strip().lower()
        if not raw:
            return default
        for c in choices:
            if raw == c.lower():
                return c
        print(f"Please choose one of: {', '.join(choices)}")


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

@dataclass
class StackGuess:
    path: str
    language: str
    framework: str
    package_manager: str = ""
    test_command: str = ""


@dataclass
class DbGuess:
    name: str = "MongoDB Atlas"
    orm: str = "Mongoose"


BACKEND_CANDIDATE_DIRS = ["server", "backend", "api", "src/server", "."]
FRONTEND_CANDIDATE_DIRS = ["client", "frontend", "web", "app", "ui"]

NODE_FRAMEWORK_DEPS = {
    "express": "Express",
    "fastify": "Fastify",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "hapi": "Hapi",
}
FRONTEND_FRAMEWORK_DEPS = {
    "@angular/core": "Angular",
    "react": "React",
    "vue": "Vue",
    "svelte": "Svelte",
    "next": "Next.js",
}
DB_DEPS = {
    "mongoose": ("MongoDB Atlas", "Mongoose"),
    "mongodb": ("MongoDB", "MongoDB driver"),
    "pg": ("PostgreSQL", "node-postgres"),
    "sequelize": ("SQL database", "Sequelize"),
    "prisma": ("SQL database", "Prisma"),
    "typeorm": ("SQL database", "TypeORM"),
}


def read_package_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guess_node_stack(dir_path: Path) -> tuple[StackGuess | None, DbGuess | None, str]:
    pkg_path = dir_path / "package.json"
    if not pkg_path.exists():
        return None, None, ""
    pkg = read_package_json(pkg_path)
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    framework = "Express"
    for dep, label in NODE_FRAMEWORK_DEPS.items():
        if dep in deps:
            framework = label
            break

    frontend_framework = None
    for dep, label in FRONTEND_FRAMEWORK_DEPS.items():
        if dep in deps:
            frontend_framework = label
            break

    db = None
    for dep, (db_name, orm_name) in DB_DEPS.items():
        if dep in deps:
            db = DbGuess(db_name, orm_name)
            break

    pm = "npm"
    if (dir_path / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (dir_path / "yarn.lock").exists():
        pm = "yarn"

    test_cmd = f"{pm} test"
    scripts = pkg.get("scripts", {})
    if "test" in scripts:
        test_cmd = f"{pm} test"

    if frontend_framework:
        return None, db, frontend_framework  # this directory is actually a frontend
    return StackGuess(path=str(dir_path.relative_to(REPO_ROOT)) if dir_path != REPO_ROOT else ".",
                       language="Node.js", framework=framework, package_manager=pm,
                       test_command=test_cmd), db, ""


def guess_python_stack(dir_path: Path) -> StackGuess | None:
    req = dir_path / "requirements.txt"
    pyproject = dir_path / "pyproject.toml"
    text = ""
    if req.exists():
        text = req.read_text(encoding="utf-8", errors="ignore").lower()
    elif pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
    else:
        return None
    framework = "Flask"
    if "django" in text:
        framework = "Django"
    elif "fastapi" in text:
        framework = "FastAPI"
    elif "flask" in text:
        framework = "Flask"
    test_cmd = "pytest"
    return StackGuess(path=str(dir_path.relative_to(REPO_ROOT)) if dir_path != REPO_ROOT else ".",
                       language="Python", framework=framework, package_manager="pip",
                       test_command=test_cmd)


def guess_go_stack(dir_path: Path) -> StackGuess | None:
    if not (dir_path / "go.mod").exists():
        return None
    framework = "net/http"
    mod_text = (dir_path / "go.mod").read_text(encoding="utf-8", errors="ignore")
    if "gin-gonic/gin" in mod_text:
        framework = "Gin"
    elif "labstack/echo" in mod_text:
        framework = "Echo"
    elif "gofiber/fiber" in mod_text:
        framework = "Fiber"
    return StackGuess(path=str(dir_path.relative_to(REPO_ROOT)) if dir_path != REPO_ROOT else ".",
                       language="Go", framework=framework, package_manager="go modules",
                       test_command="go test ./...")


def analyze() -> tuple[StackGuess | None, StackGuess | None, DbGuess]:
    backend_guess = None
    frontend_guess = None
    db_guess = DbGuess()
    found_db = False

    for d in BACKEND_CANDIDATE_DIRS:
        dir_path = (REPO_ROOT / d).resolve()
        if not dir_path.exists():
            continue
        node_backend, node_db, node_frontend_framework = guess_node_stack(dir_path)
        if node_backend and not backend_guess:
            backend_guess = node_backend
        if node_db and not found_db:
            db_guess = node_db
            found_db = True
        if node_frontend_framework and not frontend_guess:
            frontend_guess = StackGuess(
                path=str(dir_path.relative_to(REPO_ROOT)) if dir_path != REPO_ROOT else ".",
                language="TypeScript/JavaScript", framework=node_frontend_framework,
            )
        if not backend_guess:
            py = guess_python_stack(dir_path)
            if py:
                backend_guess = py
        if not backend_guess:
            go = guess_go_stack(dir_path)
            if go:
                backend_guess = go

    for d in FRONTEND_CANDIDATE_DIRS:
        if frontend_guess:
            break
        dir_path = (REPO_ROOT / d).resolve()
        if not dir_path.exists():
            continue
        _, _, node_frontend_framework = guess_node_stack(dir_path)
        if node_frontend_framework:
            frontend_guess = StackGuess(
                path=str(dir_path.relative_to(REPO_ROOT)) if dir_path != REPO_ROOT else ".",
                language="TypeScript/JavaScript", framework=node_frontend_framework,
            )

    return backend_guess, frontend_guess, db_guess


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

CONFIG_TEMPLATE = """\
# .orchestrator/config.yml
#
# Generated by .orchestrator/scripts/init-wizard.py on {generated_at}.
# This is the record of every first-run decision the wizard made or asked
# about. It is not itself read by the chatmodes/skills at runtime (they read
# the rendered instructions/agent-boundaries.yml files) — it exists so a human
# can see what was chosen without re-running the wizard, and so the wizard
# itself can be re-run idempotently later if the project's stack changes.

project:
  name: "{project_name}"
  # Each orchestrator instance targets exactly one side of the stack — the
  # chain's spec/architecture/review vocabulary and DoR/DoD are written for
  # a single codebase, not a full-stack one. Backend and frontend for this
  # feature live in separate repos, each running its own orchestrator
  # instance; companion_repo below points at the other one for cross-repo
  # spec/API-contract references.
  scope: "{project_scope}"
  companion_repo: "{companion_repo}"

backend:
  enabled: {backend_enabled}
  language: "{backend_language}"
  framework: "{backend_framework}"
  path: "{backend_path}"
  package_manager: "{backend_pm}"
  test_command: "{backend_test_cmd}"

frontend:
  enabled: {frontend_enabled}
  language: "{frontend_language}"
  framework: "{frontend_framework}"
  path: "{frontend_path}"

database:
  name: "{db_name}"
  orm: "{orm_name}"
  migrations_path: "{migrations_path}"

ticket_system:
  provider: "{provider}"
{provider_block}
stages:
  enabled: {enabled_stages}
  human_checkpoints: {human_checkpoints}

reliability:
  circuit_breaker_threshold: {circuit_breaker_threshold}

deploy:
  staging_enabled: {deploy_staging}
  production_enabled: {deploy_prod}

bot_identity:
  commit_author_name: "{bot_name}"
"""


# --------------------------------------------------------------------------
# File rewriting
# --------------------------------------------------------------------------

# Ordered (longest/most-specific first) literal replacements applied to the
# fixed set of files below. Order matters: more specific phrases must be
# replaced before the shorter substrings they contain.
def build_replacements(cfg: dict) -> list[tuple[str, str]]:
    backend_path = cfg["backend_path"]
    frontend_path = cfg["frontend_path"]
    migrations_path = cfg["migrations_path"]
    backend_language = cfg["backend_language"]
    backend_framework = cfg["backend_framework"]
    frontend_framework = cfg["frontend_framework"]
    db_name = cfg["db_name"]
    orm_name = cfg["orm_name"]

    return [
        # Paths (most specific first)
        (f"client/**/*.spec.ts", f"{frontend_path}/**/*.spec.ts"),
        (f"server/test/**", f"{backend_path}/test/**"),
        (f"server/test/unit/", f"{backend_path}/test/unit/"),
        (f"server/test/integration/", f"{backend_path}/test/integration/"),
        (f"server/models/**", f"{backend_path}/models/**"),
        (f"server/models/", f"{backend_path}/models/"),
        (f"server/routes/", f"{backend_path}/routes/"),
        (f"server/services/", f"{backend_path}/services/"),
        (f"migrations/**", f"{migrations_path}/**"),
        (f"`migrations/`", f"`{migrations_path}/`"),
        (f"migrations/<feature-slug>", f"{migrations_path}/<feature-slug>"),
        (f"server/**", f"{backend_path}/**"),
        (f"client/**", f"{frontend_path}/**"),
        (f"`server/**`", f"`{backend_path}/**`"),
        (f"`client/**`", f"`{frontend_path}/**`"),
        # Stack vocabulary (most specific first)
        ("Node.js / Express", f"{backend_language} / {backend_framework}"),
        ("Node/Express", f"{backend_language}/{backend_framework}"),
        ("Express/Node", f"{backend_framework}/{backend_language}"),
        ("Mongoose/MongoDB Atlas", f"{orm_name}/{db_name}"),
        ("MongoDB Atlas (Mongoose)", f"{db_name} ({orm_name})"),
        ("MongoDB Atlas", db_name),
        ("Mongoose", orm_name),
        ("Angular components/modules", f"{frontend_framework} components/modules"),
        ("Angular components/services", f"{frontend_framework} components/services"),
        ("Angular services", f"{frontend_framework} services"),
        ("Angular", frontend_framework),
        ("Express routes/Mongoose schemas", f"{backend_framework} routes/{orm_name} schemas"),
        ("Express routes", f"{backend_framework} routes"),
        ("Express route handlers", f"{backend_framework} route handlers"),
        ("Express app", f"{backend_framework} app"),
        ("Node services", f"{backend_language} services"),
        (" Mongo ", f" {db_name} "),
        ("Mongo collections", f"{db_name} collections"),
    ]


# Files where path/stack literal substitution is safe and applies.
TARGET_FILES = [
    ".orchestrator/agent-boundaries.yml",
    ".orchestrator/skills/context-scope.skill.md",
    ".orchestrator/automations/README.md",
    ".github/copilot-instructions.md",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy-staging.yml",
    ".github/workflows/deploy-prod.yml",
    ".github/chatmodes/architect.chatmode.md",
    ".github/chatmodes/backend-builder.chatmode.md",
    ".github/chatmodes/frontend-builder.chatmode.md",
    ".github/chatmodes/test-engineer.chatmode.md",
    ".github/chatmodes/release-engineer.chatmode.md",
    ".github/chatmodes/reviewer.chatmode.md",
    ".github/chatmodes/spec-writer.chatmode.md",
    ".github/chatmodes/eval-grader.chatmode.md",
    ".github/instructions/backend.instructions.md",
    ".github/instructions/frontend.instructions.md",
    ".github/instructions/testing.instructions.md",
    ".github/instructions/data.instructions.md",
    ".github/instructions/security.instructions.md",
    ".github/instructions/dor-dod-definitions.md",
]


def apply_replacements(cfg: dict) -> list[str]:
    replacements = build_replacements(cfg)
    touched = []
    for rel_path in TARGET_FILES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        text = original
        for old, new in replacements:
            if old == new:
                continue
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            touched.append(rel_path)
    return touched


ISSUE_TEMPLATE = """\
name: Feature Request
description: >
  Raw intake for a new feature to enter the agentic production chain. Keep this minimal — the
  real thinking-through happens in the Spec Writer agent's spec.md, not here.
title: "[Feature]: "
labels:
{labels_yaml}
body:
  - type: input
    id: feature-name
    attributes:
      label: Feature name
      description: A short, descriptive name (used to derive the feature slug).
      placeholder: "User avatar upload"
    validations:
      required: true

  - type: textarea
    id: description
    attributes:
      label: One-paragraph description
      description: >
        What do you want, roughly? Don't worry about edge cases, UX detail, or implementation —
        the Spec Writer agent will interrogate this and ask you what's missing.
      placeholder: >
        As a user, I want to upload a profile picture so my account feels more personal...
    validations:
      required: true

  - type: input
    id: requester
    attributes:
      label: Requester
      description: Who is asking for this (name, team, or "self" if you're filing it for yourself).
    validations:
      required: true

  - type: dropdown
    id: priority
    attributes:
      label: Rough priority
      options:
{priority_yaml}
    validations:
      required: true
"""


def render_issue_template(labels: list[str], priority_options: list[str]) -> str:
    labels_yaml = "\n".join(f'  - "{l}"' for l in labels)
    priority_yaml = "\n".join(f'        - "{p}"' for p in priority_options)
    return ISSUE_TEMPLATE.format(labels_yaml=labels_yaml, priority_yaml=priority_yaml)


def apply_circuit_breaker_threshold(threshold: int) -> list[str]:
    if threshold == 3:
        return []
    touched = []
    path = ORCH_DIR / "skills" / "on-start-checks.skill.md"
    if path.exists():
        original = path.read_text(encoding="utf-8")
        text = original.replace(
            "the count has reached 3", f"the count has reached {threshold}"
        )
        if text != original:
            path.write_text(text, encoding="utf-8")
            touched.append(str(path.relative_to(REPO_ROOT)))
    return touched


# --------------------------------------------------------------------------
# Jira swap
# --------------------------------------------------------------------------

JIRA_WORKFLOW_INSTRUCTIONS = """\
---
applyTo: "**"
---

# Jira Ticket Workflow — Shared Instructions

Every agent in the feature chain (`spec-writer`, `architect`, `backend-builder`, `frontend-builder`, `test-engineer`, `reviewer`, `release-engineer`) follows this file for the ticket **model** (what the fields mean, what the ticket represents) and points to `.orchestrator/skills/` for the **mechanics** (how to actually perform each recurring step). This file is policy; `.orchestrator/skills/` is procedure — don't duplicate mechanics back into this file if you're editing it.

**This integration is designed to adopt an EXISTING Jira project and its existing workflow as-is.**
It never asks for admin permission to create custom fields, add them to screens, or otherwise
change your Jira project's schema. Every piece of chain state is expressed through fields your
project already has: the issue's native `status` (moved via your workflow's own transitions,
picked by name from a configurable mapping — see `stage_status_map` below), an `agent:<name>`
label (native Jira labels, no pre-creation needed), and the issue key itself. See
`.orchestrator/docs/jira-integration.md` for the full design rationale and a worked example.

**Board reference values** (recorded by `.orchestrator/scripts/init-wizard.py`, validated
read-only by `.orchestrator/scripts/setup-jira-project.sh`):

```
JIRA_BASE_URL    = {jira_base_url}
JIRA_PROJECT_KEY = {jira_project_key}
```

> Auth: `JIRA_EMAIL` + `JIRA_API_TOKEN` must be available as environment variables/secrets wherever
> an agent runs — never hard-code them into a file in this repo. See
> `.orchestrator/docs/ops/bot-identity.md` for the credential note.

---

## 1. The ticket model, in one paragraph

One Jira issue per feature, opened once — either directly by a human, or by Spec Writer itself via
the Jira REST API at the end of an interactive spec-drafting conversation it had with a human (see
`spec-writer.chatmode.md` and `.orchestrator/automations/README.md`) — and never closed until the
feature ships. All progress lives in three places on that same issue, and they must never
disagree: a chronological thread of stage-start and stage-completion comments, the issue's native
`status` + `agent:<name>` label, and the feature's lifecycle file
(`.orchestrator/docs/features/<slug>/<issue_key>_<slug>_lifecycle.md`) — **the lifecycle file is
the source of truth** for DoR/DoD history; the issue's status/label/comments are human-readable
mirrors of it. Nobody — human or agent — should ever need to ask "what stage is this feature at" in
chat; it's always answerable from the issue, and "why did it get here" is always answerable from
the lifecycle file.

## 2. How chain state maps onto your existing Jira fields

Nothing below requires creating, renaming, or reconfiguring anything in Jira. It only requires
that you (a human, once) fill in `stage_status_map` in `.orchestrator/config.yml` with your
project's own status names.

| Chain concept | Existing Jira field used | How |
|---|---|---|
| **Stage** (`Backlog` → ... → `Done`, 11 values) | native issue `status` | `.orchestrator/scripts/update-jira-ticket.sh` looks up the target stage in `stage_status_map`, then fires whichever of the issue's *available* workflow transitions lands on that status name. Multiple stages are allowed to map to the same status (e.g. a 3-status workflow can legitimately map 4 chain stages onto `In Progress`) — the chain distinguishes them via the `Current Agent` label and the lifecycle file, not via status granularity. |
| **Current Agent** (whose turn it is, or `none`) | native issue `labels` | An `agent:<name>` label, e.g. `agent:architect`. Setting it removes any previous `agent:*` label first, so at most one is present at a time. `agent:none` (or no `agent:*` label at all) means paused for a human. |
| **Feature Slug** | the issue key itself | `.orchestrator/docs/features/<slug>/` uses the Jira issue key (e.g. `FEAT-123`) as `<slug>`, lowercased — no field needed. If your project already has a dedicated "feature slug"-like field you'd rather use instead, set `JIRA_FEATURE_SLUG_FIELD` (its custom field ID, e.g. `customfield_10050`) as an env var and the scripts will read/write that field instead of falling back to the issue key. |
| **Feature Branch** | derived by convention, not stored | `feature/<issue-key-lowercased>`, computed the same way by every agent — no field needed. Same opt-out as above via `JIRA_FEATURE_BRANCH_FIELD` if you already track branch names on the issue. |
| **`blocked` / other flags** | native issue `labels` | Plain Jira labels, added via `.orchestrator/scripts/update-jira-ticket.sh <issue-key> --field "labels" --value "blocked"`. Jira labels don't need to be pre-created the way GitHub repo labels do. |

## 3. `stage_status_map`

Recorded in `.orchestrator/config.yml` under `ticket_system.jira.stage_status_map`, one entry per
chain stage, each value being one of *your* project's actual workflow status names:

```
{stage_status_map_yaml}
```

Run `.orchestrator/scripts/setup-jira-project.sh` (read-only — it only calls `GET` endpoints) at
any time to list your project's real statuses/transitions and flag any `stage_status_map` entry
that doesn't match one, so drift between this file and a workflow that gets edited later in Jira
is caught before an agent hits it mid-run.

## 4. What every agent does, in order, every run — see `.orchestrator/skills/`

1. **On start:** [`skills/on-start-checks.skill.md`](../../.orchestrator/skills/on-start-checks.skill.md), then [`skills/dor-check.skill.md`](../../.orchestrator/skills/dor-check.skill.md).
2. **While working:** [`skills/context-scope.skill.md`](../../.orchestrator/skills/context-scope.skill.md) for what to read, [`skills/ticket-comments.skill.md`](../../.orchestrator/skills/ticket-comments.skill.md) for the "starting work" comment posted once DoR passes (post via the Jira REST API's issue-comment endpoint). Do not update `Stage` mid-work — it changes exactly once, when the stage is genuinely complete.
3. **On finish:** [`skills/dod-check.skill.md`](../../.orchestrator/skills/dod-check.skill.md), then [`skills/commit-and-handoff.skill.md`](../../.orchestrator/skills/commit-and-handoff.skill.md) for the commit trailer, status transition + label swap (via `.orchestrator/scripts/update-jira-ticket.sh`), telemetry, and completion comment.

The per-stage DoR/DoD **criteria** (as opposed to the check *procedure*, which is in the skills above) live in [`dor-dod-definitions.md`](dor-dod-definitions.md).

## 5. Automations

The polling automations described in `.orchestrator/automations/README.md` were written against
GitHub Projects v2 field filters (`Stage: X` + `Current Agent: Y`). Their Jira equivalent is a JQL
filter, e.g.:

```
project = {jira_project_key} AND status = "In Progress" AND labels = "agent:architect"
```

See `.orchestrator/docs/jira-integration.md` for the full JQL-per-stage table and for the one real
limitation of this design: Jira Cloud has no built-in cron-polling dispatcher equivalent to the
Copilot app's scheduled workflows, so stage dispatch against Jira needs either the same external
scheduler pointed at the JQL filters above, or a human manually re-running the next chatmode.

## 6. Parallel stages, human checkpoints, path boundaries

Unchanged from the mechanics described in `.orchestrator/skills/` — only the ticket backend (Jira
instead of GitHub Issues/Projects) differs, not the state machine or the stage sequence.
"""

JIRA_SETUP_SCRIPT = """\
#!/usr/bin/env bash
#
# setup-jira-project.sh
#
# READ-ONLY validation script — this is deliberately NOT a "create fields on
# my Jira project" script, because this integration is designed to adopt an
# EXISTING Jira project and its EXISTING workflow as-is (see
# .orchestrator/docs/jira-integration.md). It never calls a write/admin
# endpoint and never requires Jira admin permissions — only the same
# read access any agent already needs.
#
# What it does:
#   1. Confirms JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN can authenticate.
#   2. Lists the project's real workflow status names (per issue type).
#   3. Reads `ticket_system.jira.stage_status_map` out of
#      .orchestrator/config.yml and flags any mapped status name that isn't
#      one of the project's real statuses, so drift is caught before an
#      agent's transition attempt fails mid-run.
#   4. If JIRA_FEATURE_SLUG_FIELD / JIRA_FEATURE_BRANCH_FIELD are set, confirms
#      those custom field IDs actually exist on this Jira site.
#
# Run this any time — after first setup, and again any time the project's
# workflow changes — not just once.
#
# Requirements:
#   - `curl` and `jq` installed
#   - JIRA_BASE_URL   (e.g. https://your-domain.atlassian.net)
#   - JIRA_EMAIL      (the Jira account email for the API token below)
#   - JIRA_API_TOKEN  (create one at https://id.atlassian.com/manage-profile/security/api-tokens)
#
# Usage:
#   JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_API_TOKEN=... ./setup-jira-project.sh <PROJECT_KEY>

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <PROJECT_KEY>" >&2
  exit 1
fi

PROJECT_KEY="$1"

: "${JIRA_BASE_URL:?JIRA_BASE_URL env var must be set}"
: "${JIRA_EMAIL:?JIRA_EMAIL env var must be set}"
: "${JIRA_API_TOKEN:?JIRA_API_TOKEN env var must be set}"

command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 1; }

AUTH="${JIRA_EMAIL}:${JIRA_API_TOKEN}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.yml"

echo "==> Authenticating against ${JIRA_BASE_URL}..."
MYSELF=$(curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/myself")
echo "    Authenticated as: $(echo "${MYSELF}" | jq -r '.displayName // .emailAddress // "unknown"')"

echo "==> Confirming project '${PROJECT_KEY}' exists and is reachable..."
PROJECT_JSON=$(curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/project/${PROJECT_KEY}")
echo "    Project: $(echo "${PROJECT_JSON}" | jq -r '.name') (${PROJECT_KEY})"

echo "==> Real workflow statuses for '${PROJECT_KEY}' (per issue type)..."
STATUSES_JSON=$(curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/project/${PROJECT_KEY}/statuses")
ALL_STATUS_NAMES=$(echo "${STATUSES_JSON}" | jq -r '.[].statuses[].name' | sort -u)
echo "${STATUSES_JSON}" | jq -r '.[] | "    " + .name + ": " + ([.statuses[].name] | join(", "))'

if [[ -f "${CONFIG_FILE}" ]]; then
  echo "==> Checking stage_status_map in ${CONFIG_FILE} against real statuses..."
  MISMATCH=0
  # config.yml is written by init-wizard.py with a fixed 2-space indent under
  # `stage_status_map:` — parse it with that assumption rather than pulling in
  # a YAML library dependency for a one-off validation script.
  while IFS=':' read -r stage status; do
    stage="$(echo "${stage}" | sed -E 's/^\\s+//; s/\\s+$//')"
    status="$(echo "${status}" | sed -E 's/^\\s*"?//; s/"?\\s*$//')"
    [[ -z "${stage}" || -z "${status}" ]] && continue
    if ! echo "${ALL_STATUS_NAMES}" | grep -qxF "${status}"; then
      echo "    MISMATCH: stage '${stage}' maps to '${status}', which is not a real status on this project." >&2
      MISMATCH=1
    fi
  done < <(sed -n '/^    stage_status_map:/,/^    [a-z]/p' "${CONFIG_FILE}" | grep -E '^      [A-Za-z]')
  if [[ "${MISMATCH}" -eq 0 ]]; then
    echo "    OK: every mapped status name matches a real status on this project."
  fi
else
  echo "==> No .orchestrator/config.yml found next to this script — skipping stage_status_map check."
fi

for var in JIRA_FEATURE_SLUG_FIELD JIRA_FEATURE_BRANCH_FIELD; do
  field_id="${!var:-}"
  if [[ -n "${field_id}" ]]; then
    echo "==> Confirming ${var}=${field_id} exists on this Jira site..."
    if curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/field" | jq -e --arg id "${field_id}" '.[] | select(.id == $id)' >/dev/null; then
      echo "    OK: found."
    else
      echo "    WARNING: no field with id '${field_id}' found. Double-check the value of ${var}." >&2
    fi
  fi
done

cat <<EOF

==============================================================================
Validation complete for project '${PROJECT_KEY}'. No changes were made to
your Jira project — this script only reads.

If any MISMATCH/WARNING lines were printed above, fix them in
.orchestrator/config.yml (stage_status_map) or your JIRA_FEATURE_*_FIELD env
vars before the chain starts moving real tickets.
==============================================================================
EOF
"""

JIRA_UPDATE_SCRIPT = """\
#!/usr/bin/env bash
#
# update-jira-ticket.sh
#
# Helper used by every agent (see jira-workflow.instructions.md) to move a
# feature's Jira issue through chain state — WITHOUT any custom fields.
# Mirrors update-ticket-stage.sh's <issue-key> --field --value interface so
# the skills that call it don't need separate GitHub/Jira branches beyond the
# script name, but every field below maps onto a field your Jira project
# already has (see .orchestrator/docs/jira-integration.md):
#
#   --field "Stage"          moves the issue's native `status` by firing
#                             whichever available workflow transition lands
#                             on the status name that .orchestrator/config.yml's
#                             `ticket_system.jira.stage_status_map` maps the
#                             given chain stage to.
#   --field "Current Agent"  swaps the issue's `agent:<name>` label (removes
#                             any previous `agent:*` label first). Value
#                             "none" just removes it.
#   --field "labels"         adds an arbitrary label (e.g. "blocked"),
#                             without touching any existing labels.
#   --field "Feature Slug" / "Feature Branch"
#                             no-op by default (both are derived by
#                             convention from the issue key — see
#                             jira-workflow.instructions.md section 2) unless
#                             JIRA_FEATURE_SLUG_FIELD / JIRA_FEATURE_BRANCH_FIELD
#                             is set to an existing custom field ID, in which
#                             case that field is updated instead.
#
# Usage:
#   ./update-jira-ticket.sh <issue-key> --field "Stage" --value "Architecture Review"
#   ./update-jira-ticket.sh <issue-key> --field "Current Agent" --value "architect"
#   ./update-jira-ticket.sh <issue-key> --field "Current Agent" --value "none"
#   ./update-jira-ticket.sh <issue-key> --field "labels" --value "blocked"
#
# Requires JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN as environment variables.

set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <issue-key> --field <field-name> --value <value>" >&2
  exit 1
fi

ISSUE_KEY="$1"
shift

FIELD_NAME=""
FIELD_VALUE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --field) FIELD_NAME="$2"; shift 2 ;;
    --value) FIELD_VALUE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

: "${JIRA_BASE_URL:?JIRA_BASE_URL env var must be set}"
: "${JIRA_EMAIL:?JIRA_EMAIL env var must be set}"
: "${JIRA_API_TOKEN:?JIRA_API_TOKEN env var must be set}"
: "${FIELD_NAME:?--field is required}"
: "${FIELD_VALUE:?--value is required}"

command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 1; }

AUTH="${JIRA_EMAIL}:${JIRA_API_TOKEN}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.yml"

current_labels () {
  curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}?fields=labels" \\
    | jq -r '.fields.labels[]'
}

put_labels () {
  local labels_json="$1"
  curl -sf -u "${AUTH}" -X PUT \\
    -H "Content-Type: application/json" \\
    "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}" \\
    -d "{\\"fields\\": {\\"labels\\": ${labels_json}}}"
}

case "${FIELD_NAME}" in

  "labels")
    echo "==> Adding label '${FIELD_VALUE}' to ${ISSUE_KEY}..."
    curl -sf -u "${AUTH}" -X PUT \\
      -H "Content-Type: application/json" \\
      "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}" \\
      -d "{\\"update\\": {\\"labels\\": [{\\"add\\": \\"${FIELD_VALUE}\\"}]}}"
    echo "==> Done."
    ;;

  "Current Agent")
    echo "==> Setting Current Agent to '${FIELD_VALUE}' on ${ISSUE_KEY} (agent:* label)..."
    KEPT=$(current_labels | grep -v '^agent:' || true)
    NEW_LABELS_JSON=$(printf '%s\\n' "${KEPT}" | jq -R -s 'split("\\n") | map(select(length > 0))')
    if [[ "${FIELD_VALUE}" != "none" ]]; then
      NEW_LABELS_JSON=$(echo "${NEW_LABELS_JSON}" | jq --arg l "agent:${FIELD_VALUE}" '. + [$l]')
    fi
    put_labels "${NEW_LABELS_JSON}"
    echo "==> Done."
    ;;

  "Stage")
    echo "==> Resolving Jira status for chain stage '${FIELD_VALUE}' via stage_status_map..."
    TARGET_STATUS=$(sed -n '/^    stage_status_map:/,/^    [a-z]/p' "${CONFIG_FILE}" \\
      | grep -E "^      ${FIELD_VALUE}:" \\
      | head -n1 \\
      | sed -E 's/^[^:]+:\\s*"?//; s/"?\\s*$//')
    if [[ -z "${TARGET_STATUS}" ]]; then
      echo "ERROR: no stage_status_map entry for stage '${FIELD_VALUE}' in ${CONFIG_FILE}." >&2
      echo "       Add it under ticket_system.jira.stage_status_map (see jira-workflow.instructions.md)." >&2
      exit 1
    fi
    echo "    Target Jira status: '${TARGET_STATUS}'"

    TRANSITIONS_JSON=$(curl -sf -u "${AUTH}" "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}/transitions")
    TRANSITION_ID=$(echo "${TRANSITIONS_JSON}" | jq -r --arg s "${TARGET_STATUS}" \\
      '.transitions[] | select(.to.name == $s) | .id' | head -n1)

    if [[ -z "${TRANSITION_ID}" ]]; then
      echo "ERROR: no available transition from ${ISSUE_KEY}'s current status to '${TARGET_STATUS}'." >&2
      echo "       Available transitions right now:" >&2
      echo "${TRANSITIONS_JSON}" | jq -r '.transitions[] | "         -> " + .to.name' >&2
      echo "       Either your workflow needs an extra transition, or stage_status_map needs a" >&2
      echo "       status reachable in one hop from wherever this issue currently sits." >&2
      exit 1
    fi

    echo "==> Transitioning ${ISSUE_KEY} to '${TARGET_STATUS}' (transition id ${TRANSITION_ID})..."
    curl -sf -u "${AUTH}" -X POST \\
      -H "Content-Type: application/json" \\
      "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}/transitions" \\
      -d "{\\"transition\\": {\\"id\\": \\"${TRANSITION_ID}\\"}}"
    echo "==> Done."
    ;;

  "Feature Slug"|"Feature Branch")
    ENV_VAR="JIRA_FEATURE_SLUG_FIELD"
    [[ "${FIELD_NAME}" == "Feature Branch" ]] && ENV_VAR="JIRA_FEATURE_BRANCH_FIELD"
    FIELD_ID="${!ENV_VAR:-}"
    if [[ -z "${FIELD_ID}" ]]; then
      echo "==> '${FIELD_NAME}' is derived by convention from the issue key on ${ISSUE_KEY} —" \\
           "no field to update (set ${ENV_VAR} to override). Skipping."
      exit 0
    fi
    echo "==> Setting custom field '${FIELD_ID}' (${FIELD_NAME}) to '${FIELD_VALUE}' on ${ISSUE_KEY}..."
    curl -sf -u "${AUTH}" -X PUT \\
      -H "Content-Type: application/json" \\
      "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}" \\
      -d "$(jq -n --arg id "${FIELD_ID}" --arg val "${FIELD_VALUE}" '{fields: {($id): $val}}')"
    echo "==> Done."
    ;;

  *)
    echo "ERROR: unrecognized --field '${FIELD_NAME}'. Expected one of: Stage, Current Agent, labels, Feature Slug, Feature Branch." >&2
    exit 1
    ;;
esac
"""


def swap_to_jira(jira_base_url: str, jira_project_key: str, stage_status_map: dict[str, str]) -> list[str]:
    touched = []

    stage_status_map_yaml = "\n".join(
        f'    {stage}: "{status}"' for stage, status in stage_status_map.items()
    )

    workflow_path = GITHUB_DIR / "instructions" / "github-workflow.instructions.md"
    jira_workflow_path = GITHUB_DIR / "instructions" / "jira-workflow.instructions.md"
    content = JIRA_WORKFLOW_INSTRUCTIONS.format(
        jira_base_url=jira_base_url,
        jira_project_key=jira_project_key,
        stage_status_map_yaml=stage_status_map_yaml,
    )
    jira_workflow_path.write_text(content, encoding="utf-8")
    touched.append(str(jira_workflow_path.relative_to(REPO_ROOT)))
    if workflow_path.exists():
        workflow_path.unlink()
        touched.append(f"{workflow_path.relative_to(REPO_ROOT)} (removed)")

    jira_setup = ORCH_DIR / "scripts" / "setup-jira-project.sh"
    jira_setup.write_text(JIRA_SETUP_SCRIPT, encoding="utf-8")
    jira_setup.chmod(0o755)
    touched.append(str(jira_setup.relative_to(REPO_ROOT)))

    jira_update = ORCH_DIR / "scripts" / "update-jira-ticket.sh"
    jira_update.write_text(JIRA_UPDATE_SCRIPT, encoding="utf-8")
    jira_update.chmod(0o755)
    touched.append(str(jira_update.relative_to(REPO_ROOT)))

    # Point commit-and-handoff.skill.md at the Jira script instead of the
    # GitHub one; adjust vocabulary in copilot-instructions.md and the
    # never-list in agent-boundaries.yml.
    commit_skill = ORCH_DIR / "skills" / "commit-and-handoff.skill.md"
    if commit_skill.exists():
        text = commit_skill.read_text(encoding="utf-8")
        text = text.replace("update-ticket-stage.sh", "update-jira-ticket.sh")
        commit_skill.write_text(text, encoding="utf-8")
        touched.append(str(commit_skill.relative_to(REPO_ROOT)))

    ticket_comments_skill = ORCH_DIR / "skills" / "ticket-comments.skill.md"
    if ticket_comments_skill.exists():
        text = ticket_comments_skill.read_text(encoding="utf-8")
        text = text.replace(
            'gh label create blocked --color "B60205" --description '
            '"Escalated to a human - see on-start-checks.skill.md" 2>/dev/null || true',
            './.orchestrator/scripts/update-jira-ticket.sh <issue-key> --field "labels" --value "blocked"',
        )
        text = text.replace("GitHub issue", "Jira issue")
        ticket_comments_skill.write_text(text, encoding="utf-8")
        touched.append(str(ticket_comments_skill.relative_to(REPO_ROOT)))

    copilot_instr = GITHUB_DIR / "copilot-instructions.md"
    if copilot_instr.exists():
        text = copilot_instr.read_text(encoding="utf-8")
        text = text.replace(
            "tracked end-to-end on a single\nGitHub Issue + a GitHub Projects (v2) board.",
            "tracked end-to-end on a single\nJira issue.",
        )
        text = text.replace(
            "**The GitHub Issue + Projects board is the source of truth",
            "**The Jira issue is the source of truth",
        )
        text = text.replace(
            "`.github/instructions/github-workflow.instructions.md`",
            "`.github/instructions/jira-workflow.instructions.md`",
        )
        copilot_instr.write_text(text, encoding="utf-8")
        touched.append(str(copilot_instr.relative_to(REPO_ROOT)))

    boundaries = ORCH_DIR / "agent-boundaries.yml"
    if boundaries.exists():
        text = boundaries.read_text(encoding="utf-8")
        text = text.replace(
            '"scripts/setup-github-project.sh"', '".orchestrator/scripts/setup-jira-project.sh"'
        )
        text = text.replace(
            '".orchestrator/scripts/setup-github-project.sh"', '".orchestrator/scripts/setup-jira-project.sh"'
        )
        boundaries.write_text(text, encoding="utf-8")

    return touched


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    print("=" * 78)
    print("orchestrator startup wizard")
    print("=" * 78)
    print(f"Repo root: {REPO_ROOT}\n")

    print("Step 1/4 — analyzing the project for existing code...")
    backend_guess, frontend_guess, db_guess = analyze()
    if backend_guess:
        print(f"  Detected backend : {backend_guess.language} / {backend_guess.framework} "
              f"under `{backend_guess.path}/`")
    else:
        print("  No backend detected (greenfield, or none found in common locations).")
    if frontend_guess:
        print(f"  Detected frontend: {frontend_guess.language} / {frontend_guess.framework} "
              f"under `{frontend_guess.path}/`")
    else:
        print("  No frontend detected.")
    if backend_guess:
        print(f"  Detected database: {db_guess.name} ({db_guess.orm})")
    print()

    print("Step 2/4 — confirm or override the stack")
    project_name = ask("Project name", REPO_ROOT.name)

    # This project's backend and frontend live in separate repos, each with
    # its own orchestrator instance — never both sides in one repo. So this
    # instance is scoped to whichever side THIS repo is.
    if backend_guess and frontend_guess:
        print("  Detected both backend- and frontend-shaped code in this repo. Since backend "
              "and frontend are expected to live in separate repos, double check this repo "
              "isn't a combined checkout — then confirm below which side this particular repo "
              "actually is.")
        default_scope = "backend"
    elif frontend_guess and not backend_guess:
        default_scope = "frontend"
    else:
        default_scope = "backend"

    project_scope = ask_choice(
        "Is this repo the backend or the frontend?",
        ["backend", "frontend"], default=default_scope,
    )
    backend_enabled = project_scope == "backend"
    frontend_enabled = project_scope == "frontend"

    if backend_enabled:
        backend_language = ask("Backend language", backend_guess.language if backend_guess else "Node.js")
        backend_framework = ask("Backend framework", backend_guess.framework if backend_guess else "Express")
        backend_path = ask("Backend directory (relative to repo root)",
                            backend_guess.path if backend_guess else "server")
        backend_pm = ask("Backend package/build manager",
                          backend_guess.package_manager if backend_guess else "npm")
        backend_test_cmd = ask("Backend test command",
                                backend_guess.test_command if backend_guess else "npm test")
    else:
        backend_language = backend_framework = backend_path = backend_pm = backend_test_cmd = ""

    if frontend_enabled:
        frontend_language = ask("Frontend language",
                                 frontend_guess.language if frontend_guess else "TypeScript")
        frontend_framework = ask("Frontend framework",
                                  frontend_guess.framework if frontend_guess else "React")
        frontend_path = ask("Frontend directory (relative to repo root)",
                             frontend_guess.path if frontend_guess else "client")
    else:
        frontend_language = frontend_framework = frontend_path = ""

    has_companion = ask_yes_no(
        f"Does the {'frontend' if backend_enabled else 'backend'} for this feature live in a "
        f"separate repo the chain should know about (for cross-repo spec/API-contract "
        f"references)?",
        default=True,
    )
    if has_companion:
        companion_repo = ask(
            f"{'Frontend' if backend_enabled else 'Backend'} repo (org/name or URL)"
        )
    else:
        companion_repo = ""

    has_db = ask_yes_no("Does this project use a database the chain should know conventions for?",
                         default=backend_enabled)
    if has_db:
        db_name = ask("Database name/label", db_guess.name)
        orm_name = ask("ORM/query layer name", db_guess.orm)
        migrations_path = ask("Migrations directory", "migrations")
    else:
        db_name = orm_name = migrations_path = ""

    print("\nStep 3/4 — project/ticket management backend")
    provider = ask_choice("Use GitHub Issues + Projects, or Jira, for feature tickets?",
                          ["github", "jira"], default="github")
    provider_block = ""
    jira_base_url = jira_project_key = ""
    issue_labels: list[str] = []
    issue_priority_options: list[str] = []
    if provider == "github":
        gh_owner = ask("GitHub owner/org")
        gh_repo = ask("GitHub repo name", REPO_ROOT.name)
        issue_labels_raw = ask(
            "Label(s) to apply to new feature-request issues (comma-separated)", "feature"
        )
        issue_labels = [s.strip() for s in issue_labels_raw.split(",") if s.strip()]
        issue_priority_raw = ask(
            "Priority dropdown options for the feature-request issue form (comma-separated, in order)",
            "Low,Medium,High,Urgent",
        )
        issue_priority_options = [s.strip() for s in issue_priority_raw.split(",") if s.strip()]
        provider_block = (
            f"  github:\n"
            f"    owner: \"{gh_owner}\"\n"
            f"    repo: \"{gh_repo}\"\n"
            f"    issue_labels: {'[' + ', '.join(chr(34) + l + chr(34) for l in issue_labels) + ']'}\n"
            f"    issue_priority_options: "
            f"{'[' + ', '.join(chr(34) + p + chr(34) for p in issue_priority_options) + ']'}\n"
            f"    # run .orchestrator/scripts/setup-github-project.sh once, then record the\n"
            f"    # printed project number in .github/instructions/github-workflow.instructions.md\n"
        )
    else:
        jira_base_url = ask("Jira base URL (e.g. https://your-domain.atlassian.net)")
        jira_project_key = ask("Jira project key (e.g. FEAT)")
        print(
            "\n  This integration adapts to your EXISTING Jira workflow rather than creating new\n"
            "  custom fields — see .orchestrator/docs/jira-integration.md. For each chain stage\n"
            "  below, enter the name of the status in your project's own workflow that stage\n"
            "  should map to (it's fine — and common — for several stages to share one status;\n"
            "  the chain tells them apart via the 'agent:<name>' label instead)."
        )
        default_status_map = {
            "Backlog": "To Do",
            "Spec Drafting": "In Progress",
            "Spec Review": "In Review",
            "Architecture Drafting": "In Progress",
            "Architecture Review": "In Review",
            "Implementation": "In Progress",
            "Testing": "In Progress",
            "Governance Review": "In Review",
            "Release Prep": "In Progress",
            "PR Open": "In Review",
            "Done": "Done",
        }
        stage_status_map: dict[str, str] = {}
        for stage_name, default_status in default_status_map.items():
            stage_status_map[stage_name] = ask(
                f"  Jira status for chain stage '{stage_name}'", default_status
            )
        provider_block = (
            f"  jira:\n"
            f"    base_url: \"{jira_base_url}\"\n"
            f"    project_key: \"{jira_project_key}\"\n"
            f"    # JIRA_EMAIL / JIRA_API_TOKEN must be set as env vars/secrets wherever\n"
            f"    # agents run - never committed here.\n"
            f"    # Maps each chain stage to a status that already exists in this project's\n"
            f"    # own Jira workflow - see .orchestrator/docs/jira-integration.md. Re-run\n"
            f"    # .orchestrator/scripts/setup-jira-project.sh any time to validate this\n"
            f"    # against the real workflow (read-only, no admin access required).\n"
            f"    stage_status_map:\n"
            + "\n".join(f'      {s}: "{v}"' for s, v in stage_status_map.items())
            + "\n"
        )


    print("\nStep 4/4 — a few more first-run parameters")
    all_stages = ["spec-writer", "architect", "backend-builder", "frontend-builder",
                  "test-engineer", "reviewer", "release-engineer", "eval-grader"]
    default_stages = [s for s in all_stages
                       if (s != "backend-builder" or backend_enabled)
                       and (s != "frontend-builder" or frontend_enabled)]
    enabled_stages_raw = ask(
        "Comma-separated chain stages to enable",
        ",".join(default_stages),
    )
    enabled_stages = [s.strip() for s in enabled_stages_raw.split(",") if s.strip()]

    default_checkpoints = ["Spec Review", "Architecture Review"]
    checkpoints_raw = ask(
        "Comma-separated stages that pause for a human checkpoint",
        ",".join(default_checkpoints),
    )
    human_checkpoints = [s.strip() for s in checkpoints_raw.split(",") if s.strip()]

    circuit_breaker_threshold = int(ask("Circuit breaker threshold (consecutive fails/timeouts "
                                         "before escalating to a human)", "3"))
    deploy_staging = ask_yes_no("Enable a staging deploy workflow?", default=True)
    deploy_prod = ask_yes_no("Enable a production deploy workflow?", default=True)
    bot_name = ask("Commit author name for agent-authored commits", "copilot-agent")

    def yaml_list(items: list[str]) -> str:
        return "[" + ", ".join(f'"{i}"' for i in items) + "]"

    cfg_text = CONFIG_TEMPLATE.format(
        generated_at=__import__("datetime").datetime.now().isoformat(timespec="seconds"),
        project_name=project_name,
        project_scope=project_scope,
        companion_repo=companion_repo,
        backend_enabled=str(backend_enabled).lower(),
        backend_language=backend_language, backend_framework=backend_framework,
        backend_path=backend_path, backend_pm=backend_pm, backend_test_cmd=backend_test_cmd,
        frontend_enabled=str(frontend_enabled).lower(),
        frontend_language=frontend_language, frontend_framework=frontend_framework,
        frontend_path=frontend_path,
        db_name=db_name, orm_name=orm_name, migrations_path=migrations_path,
        provider=provider, provider_block=provider_block,
        enabled_stages=yaml_list(enabled_stages),
        human_checkpoints=yaml_list(human_checkpoints),
        circuit_breaker_threshold=circuit_breaker_threshold,
        deploy_staging=str(deploy_staging).lower(),
        deploy_prod=str(deploy_prod).lower(),
        bot_name=bot_name,
    )
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    (ORCH_DIR / "config.yml").write_text(cfg_text, encoding="utf-8")
    print(f"\nWrote {(ORCH_DIR / 'config.yml').relative_to(REPO_ROOT)}")

    print("\nApplying path/stack substitutions across chatmodes, instructions, and "
          "agent-boundaries.yml...")
    subst_cfg = dict(
        backend_path=backend_path or "server", frontend_path=frontend_path or "client",
        migrations_path=migrations_path or "migrations",
        backend_language=backend_language or "Node.js", backend_framework=backend_framework or "Express",
        frontend_framework=frontend_framework or "Angular",
        db_name=db_name or "MongoDB Atlas", orm_name=orm_name or "Mongoose",
    )
    touched = apply_replacements(subst_cfg)
    touched += apply_circuit_breaker_threshold(circuit_breaker_threshold)
    for t in touched:
        print(f"  rewrote {t}")

    if provider == "jira":
        print("\nSwapping GitHub ticket-workflow files for Jira equivalents...")
        jira_touched = swap_to_jira(jira_base_url, jira_project_key, stage_status_map)
        for t in jira_touched:
            print(f"  {t}")
    else:
        print("\nRendering .github/ISSUE_TEMPLATE/feature-request.yml with your label/priority "
              "choices...")
        issue_template_path = GITHUB_DIR / "ISSUE_TEMPLATE" / "feature-request.yml"
        issue_template_path.parent.mkdir(parents=True, exist_ok=True)
        issue_template_path.write_text(
            render_issue_template(issue_labels, issue_priority_options), encoding="utf-8"
        )
        print(f"  rewrote {issue_template_path.relative_to(REPO_ROOT)}")

    print("\n" + "=" * 78)
    print("Done. Review the diff before committing.")
    print("=" * 78)
    print("""
Not automated by this pass — review/edit by hand if relevant:
  - .orchestrator/evals/**/cases/*.md still reference the template's original
    example stack (Node/Express/Angular/MongoDB) in their scenario text.
  - .github/ISSUE_TEMPLATE/feature-request.yml is a GitHub Issue Forms file;
    if you chose Jira, ticket intake happens in Jira directly instead.
  - Deep per-stack prose in the *.instructions.md files (e.g. exact
    conventions for routing/validation/schema idioms) was vocabulary-swapped
    but not rewritten with framework-specific best practices — read them over
    for your actual stack.
  - `docs/memory/conventions.memory.md` still starts empty; that's expected,
    it fills in as features ship.
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
