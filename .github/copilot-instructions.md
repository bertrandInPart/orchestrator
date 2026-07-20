# Repository-wide Copilot instructions

This repository runs an **agentic feature production chain**: every feature moves through a
fixed sequence of specialized agents (spec-writer → architect → backend-builder /
frontend-builder → test-engineer → reviewer → release-engineer), tracked end-to-end on a single
GitHub Issue + a GitHub Projects (v2) board. The full design rationale lives in
`.orchestrator/docs/memory/decisions.memory.md` and the original build spec (kept for reference, not for
agents to re-read every run).

If you are one of the agents in `.github/chatmodes/`, **use your own chatmode file,
`.github/instructions/github-workflow.instructions.md`, and `.orchestrator/skills/` as your primary
instructions** — this file is the minimal, always-loaded context every agent (and any ad-hoc
Copilot session) should have, not a substitute for those. Chatmodes describe what's unique to a
stage; skills describe the recurring mechanics every stage shares (DoR/DoD checks, ticket
comments, lifecycle file, commit/handoff) — don't duplicate a skill's procedure back into a
chatmode.

## Ground rules for every agent, always

1. **Stay in your lane.** Each chatmode has an `allowed_write_paths` list in its frontmatter. This
   is enforced in CI by `.orchestrator/scripts/check-agent-boundaries.sh` against `.orchestrator/agent-boundaries.yml`
   — treat it as load-bearing, not descriptive.
2. **The GitHub Issue + Projects board is the source of truth for a feature's state**, not chat
   history. Read `.github/instructions/github-workflow.instructions.md` before touching any
   feature's ticket.
3. **Check `.orchestrator/docs/ops/CHAIN_PAUSED` before doing anything.** If it exists, stop immediately.
4. **Every commit carries an `Agent: <name>` trailer.** Commits without one fail CI.
5. **Specs are the durable artifact.** Write your stage's output to
   `.orchestrator/docs/features/<slug>/*.md` — if it isn't written down, the next agent can't consume it.
6. **Don't blur design and implementation.** Spec Writer and Architect do not write production
   code; Backend/Frontend Builder do not redesign the architecture mid-implementation without
   flagging it first.
7. **Spec Writer is always started by a human, interactively — never by an automation.** Every
   other stage is dispatched by a scheduled Copilot automation reacting to `Stage`/`Current Agent`
   (see `.orchestrator/automations/README.md`), but Spec Writer's whole point is a real conversation; it
   creates the GitHub issue itself once that conversation is done, not before.

## Stack (once app code exists)

- Backend: Node.js / Express, under `{{backend.path}}/**`.
- Frontend: Angular, under `{{frontend.path}}/**`.
- Database: MongoDB Atlas (Mongoose), schema/migration concerns under `data.instructions.md`.

## Where things live

- `.orchestrator/docs/features/<slug>/` — per-feature spec/architecture/notes/test-plan/review-notes.
- `.orchestrator/docs/memory/` — durable cross-feature context (conventions, past decisions). Append, don't
  rewrite.
- `.orchestrator/docs/ops/` — telemetry, the pause switch, bot identity notes.
- `.github/chatmodes/` — one file per agent role.
- `.orchestrator/skills/` — reusable procedures every agent invokes (DoR/DoD checks, ticket comments,
  lifecycle file, commit/handoff, context scope). Factor recurring mechanics here, not into
  individual chatmodes.
- `.github/instructions/` — shared and stack-scoped instructions (`applyTo:` frontmatter scopes
  each one).
- `.orchestrator/evals/` — regression harness for the chatmodes themselves (see `eval-grader.chatmode.md`).
