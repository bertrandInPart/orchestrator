# Agentic Feature Production Chain — Build Instructions

> **Purpose of this document**: This is a build spec addressed to an AI coding agent (GitHub Copilot, in agent mode). It describes how to construct a chain of specialized agents that take a feature request from idea to deployed code on a **Node.js / Angular / MongoDB Atlas** web application, using **GitHub Issues + Projects (v2)** as the ticket system that tracks every feature through the chain. It applies the principles of *The Agentic SDLC Handbook* (Daniel Meppiel): the **PROSE framework** (five constraints for reliable agent output), the seven **instrumented-codebase primitives** (Skills, Agents, Instructions, Prompts, Hooks, Memory, Plans), and **weak-form supervised execution** for governance (a human reviews outcomes at defined checkpoints rather than approving every action).
>
> **Read this whole file before creating anything.** Then scaffold the repository structure in "1. What to build," set up the GitHub ticket workflow in "2. GitHub ticket workflow," implement each agent in "3. The agent chain," wire the handoffs in "4. Orchestration & flow," close the automatic-triggering gap in "5. Dispatcher & automation hooks," and enforce isolation/idempotency in "6. Branch isolation & idempotency." Governance in "7," human checkpoints in "8," enforced path boundaries in "9," observability/circuit-breaking in "10," non-human credentials in "11. Bot identity & credentials," and testing the agents themselves in "12. Eval loop" are not optional.

---

## 0. Principles to hold constant

Before writing any file, internalize these constraints from the handbook. Every agent and instruction file you create must satisfy them:

1. **Agents build the code; humans direct the system.** Each agent below has a narrow mandate. None of them should be prompted to "just handle the whole feature" — that collapses PROSE back into vibe coding.
2. **Specs are the durable artifact, not chat transcripts.** Every stage must write its output to a versioned file in the repo (`.spec.md`, `.plan.md`, design docs, ADRs). If it isn't written down, the next agent in the chain cannot consume it.
3. **Context is the bottleneck.** Do not let every agent read the entire repo. Give each agent only the primitives (instructions, prior-stage specs, relevant skills) it needs for its stage — this is "strategic context management," the third PROSE discipline.
4. **Governance is encoded, not assumed.** Policy checks (security, PII, architecture standards) must live as checked-in rules/hooks that fail loudly, not as tribal knowledge a reviewer is expected to remember.
5. **Weak-form supervision.** A human does not approve every commit. A human reviews at three milestones: spec sign-off, architecture sign-off, and pre-deploy PR review. Between checkpoints, the chain runs agent-to-agent.
6. **The ticket is the single source of truth for where a feature stands.** One GitHub Issue per feature, moved through a Projects (v2) board by the agents themselves. Anyone — human or agent — should be able to tell a feature's state by looking at the board, without reading chat history.
7. **The chain must actually run itself.** "Agent-to-agent" in principle 5 is only real if something other than a human typing a command triggers the next stage, and every agent is safe to re-invoke without double-acting. Prefer native platform triggers over custom polling infrastructure wherever one exists, and treat idempotency as a correctness requirement, not a nice-to-have.
8. **A stated boundary that isn't enforced is a suggestion.** "Must not touch /client/**" is only real once something other than the agent's own good behavior can catch a violation, and a chain running unattended needs a way to see when something's wrong and a way to stop, not just a way to go.

---

## 1. What to build — repository scaffolding

Create this structure at the root of the web app repo (or extend it if it already exists):

```
.github/
  copilot-instructions.md          # global repo-wide instructions (always loaded)
  agent-boundaries.yml             # allowed path globs per agent (see §9)
  instructions/
    backend.instructions.md        # applies to /server/**
    frontend.instructions.md       # applies to /client/**
    data.instructions.md           # applies to /schemas/**, Mongo models
    testing.instructions.md
    security.instructions.md       # governance rules, PII rules, secrets policy
    github-workflow.instructions.md# ticket/board conventions, shared by every agent
  chatmodes/
    spec-writer.chatmode.md        # Agent 1
    architect.chatmode.md          # Agent 2
    backend-builder.chatmode.md    # Agent 3a
    frontend-builder.chatmode.md   # Agent 3b
    test-engineer.chatmode.md      # Agent 4
    reviewer.chatmode.md           # Agent 5
    release-engineer.chatmode.md   # Agent 6
    eval-grader.chatmode.md        # grades other agents' outputs against a rubric (§12.4)
  prompts/
    new-feature.prompt.md          # entry point prompt that kicks off the chain
    fix-review-comments.prompt.md
  ISSUE_TEMPLATE/
    feature-request.yml            # structured intake form for the raw feature request
  automations/
    README.md                      # documents each Copilot cloud agent automation's
                                    # trigger, prompt, and scoped tools (see §5)
  workflows/
    ci.yml                         # test + lint + security gates + boundary check (§9)
    deploy-staging.yml
    deploy-prod.yml                # gated, manual approval
    add-to-project.yml             # auto-adds new issues to the Projects (v2) board
    chain-health.yml                # scheduled stall detector (see §10)
docs/
  features/
    <feature-slug>/
      spec.md                      # output of Agent 1
      architecture.md              # output of Agent 2
      adr-*.md                     # architecture decision records, if any
      test-plan.md                 # output of Agent 4
      review-notes.md              # output of Agent 5
  memory/
    conventions.memory.md          # accumulated project conventions (see Primitive: Memory)
    decisions.memory.md            # accumulated past architecture decisions
  ops/
    agent-telemetry.jsonl          # append-only per-run log (see §10)
    CHAIN_PAUSED                   # presence of this file = kill switch, chain-wide (see §10)
    bot-identity.md                # records the GitHub App name, permissions, and secret
                                    # names used by non-Copilot workflows (see §11)
scripts/
  setup-github-project.sh          # one-time script to create the Projects (v2) board + fields
  update-ticket-stage.sh           # helper agents call to move Stage/Current Agent/Feature Branch
  check-agent-boundaries.sh        # CI script enforcing agent-boundaries.yml (see §9)
  log-agent-run.sh                 # helper agents call to append a telemetry line (see §10)
  run-agent-evals.sh               # runs an agent's eval cases through it + the grader (see §12)
evals/
  <agent-name>/
    cases/                          # eval input + answer-key files per agent (see §12.2)
    rubric.yml                      # pass/fail criteria per case
  results/
    <agent>-<date>.json             # append-only eval run history
```

Notes on why this shape:
- `.github/instructions/*.instructions.md` and `.github/chatmodes/*.chatmode.md` are Copilot-native primitives — the PROSE "Instructions" and "Agents" primitives map directly onto them. Use `applyTo:` frontmatter in instructions files to scope them to specific paths, so the backend agent isn't fed Angular conventions and vice versa.
- `docs/features/<feature-slug>/` is where every stage's output lands. This is the audit trail a human reviewer and the next agent both read from — it replaces "the agent explained it in chat."
- `docs/memory/` is the PROSE "Memory" primitive: durable, cross-feature context (naming conventions, past decisions, known gotchas) that agents append to over time instead of re-deriving from scratch each run.
- `scripts/setup-github-project.sh` exists because a Projects (v2) board and its custom fields cannot be fully defined by a committed YAML file the way `ISSUE_TEMPLATE`s or workflows can — it's created once via the `gh` CLI (see §2) and then referenced by number/URL from everywhere else.
- `.github/automations/README.md` exists because the automations themselves (§5) are configured through the Copilot app/Agents tab UI, not a file you commit — this doc is where the human-readable spec of each automation lives so it isn't tribal knowledge.
- `.github/agent-boundaries.yml` and `docs/ops/` exist because principle 8 requires boundaries and health to be *checkable*, not just documented — see §9 and §10.
- `docs/ops/bot-identity.md` exists because "however `gh` happens to be authenticated" is not an access-control policy — see §11.
- `evals/` and `eval-grader.chatmode.md` exist because nothing else in this doc actually tests whether an agent's output is good before you trust it on a real feature, or catches a regression when a chatmode/instructions file changes later — see §12.

---

## 2. GitHub ticket workflow (Issues + Projects v2)

GitHub starts completely empty. This section is what the agent should build **before** any feature work happens, so that the very first feature already has somewhere to live.

### 2.1 Ticket model
- **One GitHub Issue per feature.** Not one issue per stage. The issue is opened once (from the `feature-request.yml` template, either by a human or by Agent 1 on the human's behalf) and stays open until the feature ships. Every agent in the chain works against this same issue number for the life of the feature.
- **Progress is visible two ways on the same issue**: a running thread of stage-completion comments (a human or the next agent can read "what happened" top to bottom), and a single-select custom field on the Projects (v2) board called **`Stage`** (a human or agent can tell "what's true right now" without reading the thread).
- No separate label taxonomy for workflow state — the `Stage` field on the board is the one source of truth for where a feature is. (Non-workflow labels like `bug` vs `feature` are fine to keep; a `blocked` label is introduced in §10 for the circuit breaker specifically.)

### 2.2 The `Stage` field — values, in order

Set this up as a single-select custom field named `Stage` on the Projects (v2) board, with these options in this order:

1. `Backlog` — issue filed, no agent has started
2. `Spec Drafting` — Agent 1 is working
3. `Spec Review` — Agent 1 finished; **paused for human checkpoint #1** (see §8)
4. `Architecture Drafting` — Agent 2 is working
5. `Architecture Review` — Agent 2 finished; **paused for human checkpoint #2** (see §8)
6. `Implementation` — Agents 3a/3b are working (in parallel)
7. `Testing` — Agent 4 is working
8. `Governance Review` — Agent 5 is working
9. `Release Prep` — Agent 6 is working
10. `PR Open` — PR opened, linked to the issue; **human checkpoint #3 happens as the PR review itself** (see §8)
11. `Done` — PR merged and deployed; issue closed automatically by the "Closes #N" link in the PR

Add three more custom fields on the board while you're at it:
- **`Feature Slug`** (text) — matches the `docs/features/<slug>/` directory name, so anyone can jump from board to docs.
- **`Current Agent`** (single-select: `spec-writer`, `architect`, `backend-builder`, `frontend-builder`, `test-engineer`, `reviewer`, `release-engineer`, `none`) — whose turn it is, useful once more than one feature is in flight at once.
- **`Feature Branch`** (text) — the single Git branch this feature's work happens on, e.g. `feature/<slug>` (see §6). Every agent checks out this exact branch rather than assuming one.

### 2.3 One-time setup: `scripts/setup-github-project.sh`

Write this script using the `gh` CLI (`gh project create`, `gh project field-create`, `gh project field-create --single-select-options`) to create the board and the four fields above. This is a **run-once, by a human, before the first feature** step — it is infrastructure, not something an agent re-creates per feature. Document at the top of the script that it takes the repo's `owner/name` as an argument and prints the resulting project number, which should then be recorded in `github-workflow.instructions.md` so every agent knows which board to update.

### 2.4 `feature-request.yml` — the intake template

A GitHub Issue Form (not a bare `.md` template) with fields for: feature name, one-paragraph description, requester, and rough priority. Keep it minimal — this is the *raw* request; the actual thinking-through happens in Agent 1's spec, not in the intake form. This is what a human fills out to start the chain, or what Agent 1 fills out on the human's behalf if the request arrived as a chat message rather than a filed issue.

### 2.5 How each agent must interact with the ticket

Every `.chatmode.md` file (§3) must include this behavior, so put the shared mechanics in `github-workflow.instructions.md` and have every chat mode reference it, rather than repeating it six times:

1. **On start**:
   - Check `docs/ops/CHAIN_PAUSED` first (see §10.4) — if it exists, stop immediately without acting.
   - Read the issue (by number, passed in as the agent's input) to get the feature slug, feature branch, and any human comments left since the last stage.
   - Run the idempotency check from §6.2 — a re-invocation of an already-completed stage should reconcile, not redo.
   - Check the consecutive-failure count for this stage (§10.3) — if it's already tripped the circuit breaker, stop and flag rather than trying again.
2. **While working**: tag every commit with an `Agent: <agent-name>` trailer (see §9.2) — this is what makes boundary enforcement possible after the fact.
3. **On finish**:
   - Set `Stage` to the value representing "this stage is done" (e.g. Agent 1 sets `Spec Drafting` → `Spec Review`).
   - Set `Current Agent` to `none` if the next step is a human checkpoint, or to the next agent's name if the chain continues automatically.
   - Post one structured comment on the issue: what was done, a link to the doc it wrote, and — for Agent 1 — the open questions inline, not just in the file.
   - Append one line to `docs/ops/agent-telemetry.jsonl` via `scripts/log-agent-run.sh` (see §10.1).
4. **Never** move `Stage` backward except when Agent 5 (Reviewer) sends work back to Agents 3a/3b on a FAIL — the one legitimate "back" transition, logged as a comment explaining why.

### 2.6 `add-to-project.yml` — the one piece of Actions-based automation

This is the only GitHub Actions workflow involved in ticket movement itself, and it does the smallest possible thing: on `issues.opened`, add the new issue to the Projects (v2) board and set `Stage` to `Backlog`. It does **not** move tickets between stages — that stays the agents' job. (Stage-to-stage dispatching is handled separately, in §5, by Copilot's own automation mechanism; `chain-health.yml` in §10 is a second, unrelated Actions workflow that only watches for stalls, it doesn't move anything either.)

---

## 3. The agent chain

Each agent is a `.chatmode.md` file with a single mandate, explicit inputs, explicit outputs, an explicit "do not" list, and the shared ticket-handling behavior from §2.5. Build them in this order.

### Agent 1 — Spec Writer (`spec-writer.chatmode.md`)
- **Mandate**: Turn a one-paragraph feature request (or ticket) into a structured, testable spec. This agent's job is explicitly **not** to be agreeable — a spec writer that just formats whatever the requester said is a stenographer, not the first quality gate in the chain. It must push back, surface what wasn't thought through, and refuse to consider the spec done until the human has actually answered the hard questions.
- **Reads**: the GitHub issue (feature request + any human comments); `docs/memory/conventions.memory.md`.
- **Writes**: `docs/features/<slug>/spec.md` containing: problem statement, user stories, explicit acceptance criteria (Given/When/Then), edge cases, UX walkthrough, out-of-scope list, and open questions for the human — see the mandatory structure below. Also creates the GitHub issue from `feature-request.yml` if one doesn't exist yet, creates the `feature/<slug>` branch (see §6.1), and sets `Feature Slug` / `Feature Branch` on the board.
- **Must NOT**: propose implementation details, choose libraries, or write code. It also must **not** silently fill gaps with reasonable-sounding assumptions and mark the spec ready — an unresolved question belongs in the "Open Questions" section, blocking checkpoint #1, not smoothed over. Enforced per §9: this agent's allowed paths are `docs/features/**` only.
- **Checkpoint**: 🛑 human reviews and approves `spec.md` before Agent 2 starts (see §8). The human checkpoint should feel like answering a short, sharp interview, not rubber-stamping a document — if the agent hasn't given the human anything to react to or correct, it hasn't done its job.
- **Ticket behavior**: sets `Stage` to `Spec Drafting` on start, then to `Spec Review` and `Current Agent` to `none` on finish, and posts the open questions directly in the issue comment (not only inside `spec.md`).

**Required behavior — the interrogation pass.** Before writing `spec.md`, the agent must run an explicit questioning pass over the feature request and hand the output to the human as a numbered list inside the spec's "Open Questions" section. It should draw from these four angles every time, adapting them to the actual feature rather than asking generically:

1. **Scope & intent probing** — What problem is this actually solving, and for whom? Is there an existing workaround being replaced? What does "done" look like from the user's perspective, not the developer's? What's explicitly *not* included, and does the requester agree with that boundary?
2. **Edge cases and failure modes** — Work through these categories every time and only omit a category if it's genuinely inapplicable (state why, don't just skip it):
   - **Empty/boundary states**: no data yet, first-time use, exactly one item, maximum allowed items, pagination edges.
   - **Concurrency & race conditions**: two users editing the same record, a request in flight when the underlying data changes, double-submit on slow networks.
   - **Permission & identity edge cases**: unauthenticated access, expired session mid-action, a user who has permission for the object but not the action, role changes mid-session.
   - **Input validation & malformed data**: unexpected characters/encodings, oversized payloads, partially-filled forms, copy-pasted data with hidden whitespace/formatting.
   - **Failure & degraded states**: MongoDB Atlas connection drop mid-write, slow network / timeout, a downstream service unavailable, partial writes needing rollback or idempotency.
   - **State transitions**: what happens to in-flight or previously-created data when the feature changes an existing model; migration/backfill implications.
   - **Cross-feature interaction**: does this collide with an existing feature, quota, or business rule elsewhere in the app?
3. **UX sense-check** — The agent must reason through the flow as a first-time user would experience it, not just as a data model. For every new or changed screen/interaction, it must explicitly answer:
   - What does the user see in the **empty state**, the **loading state**, the **error state**, and the **success state**? A spec that only describes the happy path is incomplete.
   - Is the action **destructive or irreversible**? If so, is confirmation, undo, or a warning required — and has the requester actually decided that, or is the agent about to assume it?
   - Is there a simpler existing UI pattern in the app this should reuse, or is a new pattern being introduced? New patterns should be flagged as a question, not adopted silently.
   - How does this behave on **mobile / narrow viewports** if the app is responsive, and does it change the interaction (e.g. a modal vs. a full-screen flow)?
   - What feedback does the user get during async operations (spinners, optimistic UI, disabled buttons) — and is that consistent with how the rest of the app behaves?
   - Accessibility basics: keyboard reachability, focus handling after the action completes, and screen-reader-sensible labeling for anything new.
4. **Non-functional pressure-testing** — Rough expected volume/scale, any performance expectation implied by the request, any data sensitivity (PII, payment info) that changes how this must be handled, and whether this needs a feature flag or staged rollout given its blast radius.

The agent should not ask every possible question mechanically — it should read the specific feature request, identify which of the above categories are genuinely ambiguous or unaddressed *for this feature*, and ask only those, but ask them **specifically** (tied to the actual feature, not generic templates) and **exhaustively enough that checkpoint #1 is a real decision point**, not a formality.

**Required `spec.md` structure:**

```markdown
# Feature: <name>

## Problem Statement
<what problem, for whom, why now>

## User Stories
<As a ___, I want ___, so that ___>

## UX Walkthrough
<step-by-step flow through the feature as a user would experience it,
including empty/loading/error/success states for each screen touched>

## Acceptance Criteria
<Given/When/Then, one block per behavior>

## Edge Cases
<one bullet per edge case identified, grouped by the categories above,
each phrased as a testable statement, not just a note>

## Explicitly Out of Scope
<what this feature will NOT do, so Agent 2 doesn't scope-creep>

## Open Questions (BLOCKING — must be answered before checkpoint #1 passes)
1. <question>
2. <question>
...
```

If the human answers the open questions in a way that changes the acceptance criteria or edge cases, the agent should be re-invoked to update `spec.md` before it's considered approved — the spec is not final until the open questions section is empty.

### Agent 2 — Architect (`architect.chatmode.md`)
- **Mandate**: Turn the approved spec into an implementation plan: which Angular components/modules, which Express/Node routes and services, which Mongo collections/schemas change, and how they compose. Also size the work so each downstream stage fits inside a single agent session (see §5.4) — if the feature is large, say so explicitly and propose a split.
- **Reads**: `spec.md`, the GitHub issue thread, `docs/memory/decisions.memory.md`, existing schema/route conventions.
- **Writes**: `docs/features/<slug>/architecture.md` (component/route/schema breakdown, sequence of work, risk notes) and an `adr-*.md` for any decision that deviates from existing conventions.
- **Must NOT**: write production code. This is design, not implementation — keep the deterministic/probabilistic seam clean. Enforced per §9: allowed paths are `docs/features/**` only.
- **Checkpoint**: 🛑 human reviews and approves `architecture.md` before implementation starts.
- **Ticket behavior**: only starts once `Stage` has been moved past `Spec Review` by the human (see §8). Sets `Stage` to `Architecture Drafting` on start, then `Architecture Review` / `Current Agent: none` on finish, with a comment summarizing the plan and linking `architecture.md`.

### Agent 3a — Backend Builder (`backend-builder.chatmode.md`)
- **Mandate**: Implement the Node/Express routes, services, and Mongoose/Mongo schema changes described in `architecture.md`.
- **Reads**: `architecture.md`, `backend.instructions.md`, `data.instructions.md`.
- **Writes**: code under `/server/**`, plus a short `docs/features/<slug>/backend-notes.md`. Commits go on `Feature Branch`, tagged `Agent: backend-builder`.
- **Must NOT**: touch `/client/**`, deploy anything, or modify CI/CD config. Enforced per §9: allowed paths are `server/**` and `docs/features/**` only.
- **Ticket behavior**: on start (of either 3a or 3b, whichever runs first), sets `Stage` to `Implementation`; each posts its own completion comment, and `Stage` only advances to `Testing` once **both** have posted.

### Agent 3b — Frontend Builder (`frontend-builder.chatmode.md`)
- **Mandate**: Implement the Angular components, services, and routing described in `architecture.md`.
- **Reads**: `architecture.md`, `frontend.instructions.md`.
- **Writes**: code under `/client/**`, plus `docs/features/<slug>/frontend-notes.md`. Commits go on the same `Feature Branch`, tagged `Agent: frontend-builder`.
- **Must NOT**: touch `/server/**` or schema files. Enforced per §9: allowed paths are `client/**` and `docs/features/**` only.
- Runs in parallel with Agent 3a where the architecture doc marks the API contract as fixed.
- **Ticket behavior**: same as Agent 3a — whichever finishes last advances `Stage` to `Testing`.

### Agent 4 — Test Engineer (`test-engineer.chatmode.md`)
- **Mandate**: Write and run unit + integration tests against the acceptance criteria in `spec.md`, not just against the code that was written.
- **Reads**: `spec.md`, `architecture.md`, the new code, `testing.instructions.md`.
- **Writes**: test files, plus `docs/features/<slug>/test-plan.md`.
- **Must NOT**: modify implementation code to make a failing test pass without flagging it. Enforced per §9: allowed paths are `**/*.test.*`, `**/*.spec.*`, test directories, and `docs/features/**` only.
- **Ticket behavior**: sets `Stage` to `Governance Review` on finish.

### Agent 5 — Reviewer / Governance Gate (`reviewer.chatmode.md`)
- **Mandate**: Review the diff against `security.instructions.md` and general code-quality standards.
- **Reads**: the full diff, `security.instructions.md`, `architecture.md`.
- **Writes**: `docs/features/<slug>/review-notes.md`. Enforced per §9: allowed paths are `docs/features/**` only — this agent reviews, it doesn't touch code.
- **Must NOT**: merge or approve the PR itself.
- **Ticket behavior**: on FAIL, moves `Stage` back to `Implementation`, sets `Current Agent`, comments with blocking issues, and increments the failure counter used by the circuit breaker (§10.3). On PASS, moves `Stage` to `Release Prep` and resets that counter.

### Agent 6 — Release Engineer (`release-engineer.chatmode.md`)
- **Mandate**: Prepare the release — changelog entry, migration scripts for Mongo Atlas if schema changed, feature-flag wiring if applicable, and the PR description.
- **Reads**: everything in `docs/features/<slug>/`.
- **Writes**: PR description, changelog, migration script (if any). Opens the PR from `Feature Branch`. Enforced per §9: allowed paths are `docs/features/**`, `CHANGELOG.md`, and migration script directories — explicitly **not** `.github/workflows/deploy-*.yml`.
- **Must NOT**: trigger production deploy directly, or touch deploy workflow files.
- **Ticket behavior**: opens the PR with `Closes #<issue-number>`, sets `Stage` to `PR Open`.

---

## 4. Orchestration & flow

```
[Feature request → GitHub Issue #N, Stage: Backlog]
      │
      ▼
 Agent 1: Spec Writer ───────► docs/features/<slug>/spec.md
      │                         Stage: Spec Drafting → Spec Review
      ▼
   🛑 HUMAN CHECKPOINT #1 — approve spec (on the issue thread; see §8)
      │
      ▼
 Agent 2: Architect ─────────► docs/features/<slug>/architecture.md
      │                         Stage: Architecture Drafting → Architecture Review
      ▼
   🛑 HUMAN CHECKPOINT #2 — approve architecture
      │
      ├──────────────┬───────────────┐
      ▼              ▼               │
 Agent 3a: Backend  Agent 3b: Frontend│  (parallel, API contract frozen by architecture.md)
      │              │               │   Stage: Implementation
      └──────┬───────┘               │
             ▼                       │
     Agent 4: Test Engineer ─────────┘
             │                          Stage: Governance Review
             ▼
     Agent 5: Reviewer (governance gate)
             │
        PASS │ FAIL ──► Stage: Implementation (back to Agent 3a/3b, with review-notes.md)
             ▼             [3 consecutive FAILs → circuit breaker trips, §10.3]
     Agent 6: Release Engineer ──► PR opened, "Closes #N"
             │                       Stage: PR Open
             ▼
   🛑 HUMAN CHECKPOINT #3 — PR review & merge (native GitHub PR review)
             │
             ▼
   CI: staging deploy (automatic) → manual gate → production deploy → Stage: Done
        (CI also runs the §9 boundary check on every push)
```

Practical implementation notes for GitHub Copilot specifically:
- Use `.prompt.md` files (the "Prompts" primitive) as the reusable entry points for a stage — §5 covers what actually fires these automatically instead of a human running them by hand.
- Each `.chatmode.md` should declare in its frontmatter exactly which tools/scopes it needs — don't grant every agent full repo write access. This is the context-management discipline applied to permissions, and it's the first line of defense that §9's CI check backs up.
- After each agent finishes, have it append one line to `docs/memory/conventions.memory.md` or `decisions.memory.md` if it made a reusable decision.

---

## 5. Dispatcher & automation hooks (closing the orchestration gap)

A chain where a human runs a command by hand at every stage is not yet orchestration. This section uses GitHub Copilot's own automation mechanism rather than bespoke polling infrastructure, per principle 7.

### 5.1 The real mechanism: Copilot cloud agent automations

GitHub Copilot's cloud agent supports **automations** — saved tasks that run on a trigger without a human starting them by hand. As of this writing, the available triggers are: on a schedule (hourly, daily, or weekly), when an issue is created, when a pull request is opened, and when a pull request is synchronized — each event-based trigger can be narrowed with a search-query filter. Automations only run in response to events from users with write access to the repo, limiting prompt-injection risk. Each automation is scoped to a single repo, with a name, prompt, a set of tools it's allowed to use, and an optional model choice. Automations require a private/internal repo with the cloud agent policy enabled. **This is an actively evolving product surface — verify the current trigger list against GitHub's docs before building against it.**

### 5.2 Mapping automations onto the chain

- **Kicking off Agent 1**: the native "when an issue is created" trigger, filtered to issues from `feature-request.yml`.
- **Agent-to-agent handoffs with no human in between**: one scheduled automation per agent (e.g. every 15–30 minutes), self-checking `Current Agent`/`Stage` so a shared cadence is safe.
- **The two human-gated handoffs**: deliberately no automation — the human re-assigning the issue to Copilot is both the approval and the trigger.
- **Reviewer FAIL → back to Implementation**: same scheduled-automation pattern, picked up once `Current Agent` names the builder again.

### 5.3 Document what you configure

Write `.github/automations/README.md` listing, for each automation: name, trigger, prompt text, and granted tools.

### 5.4 Session-length constraint

Cloud agent sessions have a hard execution-time ceiling per session (on the order of an hour) and one branch/one PR per task. Agent 2 is responsible for sizing work so a stage fits in one session, or explicitly splitting it into sequential sub-tasks.

### 5.5 Circuit breaker and pause switch hook into automations too

Every automation's prompt (§5.2) must include the same two checks as §2.5's "on start": check `docs/ops/CHAIN_PAUSED` first and no-op if present, and check the stage's consecutive-failure count before acting. See §10 for the mechanics both of these depend on.

---

## 6. Branch isolation & idempotency

### 6.1 One branch per feature, named explicitly

- Agent 1 creates `feature/<slug>` at the very start and records it in the `Feature Branch` board field.
- Every later agent's "on start" step reads `Feature Branch` and checks out **that exact branch** — never assumes, guesses, or creates a new one.
- Verify empirically (run two features concurrently in a test repo) that this keeps them isolated, since exact session/branch reuse behavior across multiple automation runs against one long-lived issue is worth confirming against current product behavior.

### 6.2 Idempotency — every agent must be safe to re-invoke

- **Before writing an output file**: if it already exists **and** `Stage` is already past this agent's stage, treat the run as a duplicate trigger and exit without acting.
- **Before posting a completion comment**: search the thread for an existing comment with this stage's header; don't post a second.
- **Before moving `Stage` forward**: read the current value first; if already at or past the target, no-op.
- **Reviewer's backward transition**: recognize its own prior FAIL comment before posting a duplicate.

---

## 7. Governance gates (encode these before the chain goes live)

Per the handbook's governance chapter: **what you don't restrict, an agent will eventually touch.** Encode these as CI checks and/or `security.instructions.md` rules, not as reviewer memory:

- Any change touching user PII or auth requires the Reviewer agent to explicitly cite the relevant rule in `review-notes.md` and requires a named human sign-off in the PR — this cannot be waived by an agent.
- Schema migrations against MongoDB Atlas must be reviewed for backward compatibility (no destructive field drops without a documented migration path).
- Secrets/connection strings never appear in generated code — enforce via a pre-commit hook and a CI secret-scan step.
- No agent may edit `.github/workflows/deploy-prod.yml` or bypass the manual-approval gate on it — this is now also mechanically enforced, not just stated, per §9.
- The Reviewer agent's PASS/FAIL is advisory context for the human, not a merge gate by itself — CI checks are the actual automated merge gate.
- No agent may move a ticket's `Stage` field backward except Agent 5 on a FAIL.
- Each automation (§5) is granted only the tools its stage actually needs.
- **Path boundaries per agent are enforced in CI, not just documented — see §9.**
- **Every stage run is logged and a repeated-failure circuit breaker exists — see §10.**

---

## 8. Human checkpoints (weak-form supervision — non-negotiable)

Per your choice of weak-form supervision, the chain runs autonomously between these three points, but does not cross them without a human. The `Stage` field makes the pause visible — the agent stops and waits at `Spec Review` / `Architecture Review`, and only proceeds once the human says so, at which point re-assigning the issue to Copilot is both the approval and the trigger for the next stage.

1. **After Agent 1 (spec) — `Stage: Spec Review`.** Answer the agent's open questions and confirm the acceptance criteria match what was asked. If the spec came back with an empty "Open Questions" section for a non-trivial feature, treat that as under-interrogation, not simplicity — send it back.
2. **After Agent 2 (architecture) — `Stage: Architecture Review`.** Confirm the technical approach before code gets written against it — this is where compliance/PII/architecture-standard issues from §7 should surface.
3. **At PR review (post Agent 6) — `Stage: PR Open`.** This checkpoint *is* GitHub-native — the ordinary PR review every merge already requires, now backed by `spec.md`, `architecture.md`, `test-plan.md`, and `review-notes.md` as reviewable artifacts.

---

## 9. Boundary enforcement (CI-enforced path restrictions)

Every agent's "Must NOT touch X" rule in §3 is currently something an agent could violate under pressure — a large refactor that seems to require touching one forbidden file, an agent "helpfully" fixing something adjacent. This section makes those boundaries mechanically checkable instead of just documented, closing principle 8's gap.

### 9.1 `.github/agent-boundaries.yml` — the allow-list

```yaml
# Each agent may only modify files matching its listed globs.
# Paths not listed for an agent are forbidden to that agent, full stop.
spec-writer:
  - "docs/features/**"
architect:
  - "docs/features/**"
backend-builder:
  - "server/**"
  - "docs/features/**"
frontend-builder:
  - "client/**"
  - "docs/features/**"
test-engineer:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "server/test/**"
  - "client/test/**"
  - "docs/features/**"
reviewer:
  - "docs/features/**"
release-engineer:
  - "docs/features/**"
  - "CHANGELOG.md"
  - "migrations/**"

# No agent, regardless of role, may touch these paths under any circumstance.
# A violation here fails CI even if the agent's own allow-list would permit it.
never:
  - ".github/workflows/deploy-prod.yml"
  - ".github/agent-boundaries.yml"
  - "scripts/setup-github-project.sh"
```

### 9.2 Commit tagging convention

Every commit an agent makes must include a trailer identifying which agent made it:

```
<commit subject>

<commit body>

Agent: backend-builder
```

This is what makes enforcement possible after the fact — without it, a CI check has no way to know which agent is responsible for which changed file in a multi-agent branch history.

### 9.3 `scripts/check-agent-boundaries.sh` — the CI enforcement script

This script, run as a job in `ci.yml` on every push to a `feature/**` branch and on every PR:
1. Walks the commit log for the branch (or the PR's commit range).
2. For each commit, reads the `Agent:` trailer. A commit with no trailer, or an unrecognized agent name, fails CI immediately — no silent skip.
3. For each file changed in that commit, checks it against that agent's allow-list in `agent-boundaries.yml`, and separately against the `never` list.
4. Fails the build, printing the offending commit SHA, agent, and specific file, if any file falls outside the agent's allow-list or inside `never`.

This runs as a required CI check — a PR cannot merge (checkpoint #3, §8) if it fails, same as any other required check.

### 9.4 Why CI and not a pre-commit hook alone

A pre-commit hook is easy for an agent under pressure to bypass (`--no-verify`) or simply not have installed in its session environment. CI is the backstop that always runs regardless of what happened locally — treat the hook (if you add one) as a fast local warning, and the CI job as the actual gate.

---

## 10. Observability & circuit breaker

Nothing so far tracks whether a stage is taking unusually long, failing repeatedly, or silently stuck — and nothing lets you halt the whole chain quickly if something's clearly wrong. This section closes that gap.

### 10.1 Per-run telemetry: `docs/ops/agent-telemetry.jsonl`

Every agent, on finish (§2.5), calls `scripts/log-agent-run.sh` to append one JSON line:

```json
{"feature_slug":"user-avatar-upload","issue_number":42,"agent":"backend-builder","stage":"Implementation","started_at":"2026-07-08T10:03:00Z","finished_at":"2026-07-08T10:41:00Z","duration_seconds":2280,"outcome":"success","attempt_number":1}
```

`outcome` is one of `success`, `fail`, or `timeout`. This file is append-only and repo-committed, so it's queryable with plain `jq` — no external monitoring service required to get basic answers to "how long does the Architect stage usually take" or "which stage fails most often."

### 10.2 `scripts/log-agent-run.sh`

A small wrapper (parallel in spirit to `update-ticket-stage.sh`) that takes the fields above as arguments and appends a validated JSON line to `docs/ops/agent-telemetry.jsonl`, committing it as part of the agent's own commit so it travels with the rest of that stage's changes.

### 10.3 Circuit breaker — stop after repeated failures on the same stage

Derive the consecutive-failure count for a given issue + stage directly from `agent-telemetry.jsonl` (no separate counter file to keep in sync): count trailing `fail`/`timeout` entries for that `issue_number` + `stage` since the last `success`. Before acting (§2.5 "on start," §5.5), an agent checks this count:

- **If it's reached 3**: do not attempt the stage again. Instead: set `Current Agent` to `none`, add a `blocked` label to the issue, and post a comment summarizing the failures and tagging a human for manual intervention. This is what stops an agent from burning compute/premium requests in an automated retry loop nobody's watching.
- A human clearing the `blocked` label (after fixing whatever was wrong, or deciding to intervene manually) is what resets the cycle — the next automation run sees the label gone and the count is naturally superseded once a fresh `success` lands.

### 10.4 Kill switch: `docs/ops/CHAIN_PAUSED`

A single committed file whose mere presence means "stop everything." Every agent (§2.5) and every automation prompt (§5.5) checks for this file before doing anything else, chain-wide, regardless of which feature or stage. A human adds this file (one commit) to halt the entire system immediately — for a bad deploy, a runaway agent, or just wanting to freeze things during an incident — and removes it (another commit) to resume. This is deliberately the bluntest possible instrument: no per-feature or per-agent granularity, because an emergency stop that requires deciding which of eleven scopes to disable is not a fast emergency stop.

### 10.5 Stall detector: `chain-health.yml`

A scheduled GitHub Actions workflow (e.g. every few hours) — separate from the per-agent Copilot automations in §5 — that scans open feature issues and flags (via a comment, not an automatic action) any issue where `Stage` hasn't changed in longer than a reasonable threshold (e.g. 24 hours) while `Current Agent` is not `none`. This catches the case the circuit breaker doesn't: not repeated failure, but silent inactivity — an automation that should have picked up work but didn't, for reasons the chain itself can't detect from the inside.

---

## 11. Bot identity & credentials

Right now every script and workflow in this doc assumes "however `gh` happens to be authenticated" — in practice, a developer's personal token. That's wrong for a system meant to run unattended: revoking access means tracking down whose token it was, and audit logs show a person's name for actions a system actually took.

### 11.1 Two identities, two different problems

- **Actions taken inside a Copilot cloud agent automation** — issue comments, commits, PR creation, field edits via the automation's own tool grants — already run under GitHub's built-in Copilot bot actor. There's nothing to set up here; the automation's tool allow-list (§5.1, reinforced by §9) is what actually scopes these actions, not a credential you manage.
- **Actions taken by anything outside that sandbox** — the one-time `setup-github-project.sh`, the `add-to-project.yml` and `chain-health.yml` Actions workflows, and `check-agent-boundaries.sh` in CI — need an explicit, non-human identity. This is the actual gap.

### 11.2 Use a GitHub App, not a personal PAT, for the unattended workflows

Create a narrowly-scoped GitHub App (e.g. named `feature-chain-automation`), installed only on this repo, granted only: Issues (read/write), Pull requests (read/write), Projects (read/write), and Contents (read-only — no workflow in this doc needs to push commits itself; all code changes travel through Copilot's own commit path). Store its App ID and private key as repository secrets (`CHAIN_BOT_APP_ID`, `CHAIN_BOT_PRIVATE_KEY`). Have `add-to-project.yml` and `chain-health.yml` exchange those for a short-lived installation token at the start of the job (via the standard GitHub App token-generation action) instead of relying on the default `GITHUB_TOKEN` or a developer's PAT. Record the App's name, permissions, and secret names in `docs/ops/bot-identity.md` so this isn't tribal knowledge either.

### 11.3 A concrete, known gotcha this solves

Worth flagging explicitly: the default `GITHUB_TOKEN` Actions provides to a workflow does not, by default, carry access to Projects (v2) — its scope doesn't cover the Projects v2 API. This is exactly why `add-to-project.yml` needs the App-based token from §11.2 rather than the default token; without it, the workflow authenticates fine but fails the moment it tries to touch the board. Confirm this against current GitHub documentation before building — token scoping for Projects v2 is the kind of thing that can change.

### 11.4 What NOT to do

- **Don't reuse the App for `setup-github-project.sh`.** That script is a deliberate, one-time human action — keep it tied to the human's own `gh auth` session so creating the board itself is naturally audited as a person's action, not folded into the system's identity.
- **Don't put the App's private key or any PAT anywhere except repository/organization secrets** — never in a committed `.env` file, never printed in a log, never passed as a bare script argument (arguments can leak into shell history and CI logs).
- **Don't grant the App more than it needs.** No workflow in this doc requires `Contents: write` — least privilege applies to the bot's permissions exactly as it applies to each chatmode's file scope (§9).

### 11.5 Tie it back into the boundary and secret-scanning checks

The App's credential values should never appear in a commit from any agent — this is exactly what the secret-scan CI step (§7) already exists to catch, and `check-agent-boundaries.sh` (§9.3) should treat a commit touching `docs/ops/bot-identity.md`'s secret *names* (not values, which are never committed) as a signal worth a closer look, not a routine change.

---

## 12. Eval loop — testing the agents themselves

Everything so far assumes each `.chatmode.md` actually does what its mandate says. Nothing yet checks that assumption before you trust an agent on a real feature, or catches a regression when someone edits a chatmode or instructions file six months from now. This section closes that gap.

### 12.1 Why this is harder than testing code, and what to do about it

A chatmode is a prompt, not a function — there's no single "correct" `spec.md` to diff against, and re-running the same input twice can yield different (both acceptable) outputs. So the eval harness can't be a normal assertion-based test suite; it needs to be **rubric-graded**: for each test case, a checklist of properties the output must have, graded by a second pass rather than an exact-match comparison.

### 12.2 `evals/` structure

```
evals/
  spec-writer/
    cases/
      001-underspecified-request.md   # deliberately vague input
      002-destructive-action.md       # input implies a delete/irreversible action
      003-trivial-feature.md          # input is genuinely simple — checks the agent
                                       # doesn't over-ask on something that doesn't need it
      004-concurrency-prone.md        # input implies multi-user editing of shared state
    rubric.yml                        # pass/fail criteria per case, see §12.3
  architect/
    cases/
    rubric.yml
  reviewer/
    cases/
    rubric.yml
  results/
    <agent>-<date>.json                # append-only eval run history, see §12.5
```

Every case file has two parts: the raw input the agent would actually receive, and an **answer key** — not the expected spec text, but the specific things a good response must contain (e.g. for `002-destructive-action.md`: "must explicitly ask whether the delete requires confirmation or is undoable; must not silently assume either answer").

### 12.3 `rubric.yml` — what "pass" means for a given agent

```yaml
# evals/spec-writer/rubric.yml
criteria:
  - id: asks-open-questions
    description: "Open Questions section is non-empty for any non-trivial case"
    applies_to: ["001", "002", "004"]
  - id: no-open-questions-when-trivial
    description: "Open Questions section is empty or near-empty for genuinely simple cases"
    applies_to: ["003"]
  - id: flags-destructive-action
    description: "explicitly raises confirmation/undo as an open question when the
                   feature involves delete or other irreversible action"
    applies_to: ["002"]
  - id: covers-concurrency
    description: "Edge Cases section includes at least one concurrency/race-condition item
                   when the feature implies shared, multi-user state"
    applies_to: ["004"]
  - id: no-implementation-detail
    description: "spec.md contains no library names, route paths, or schema field names —
                   that's the Architect's job, not the Spec Writer's"
    applies_to: ["001", "002", "003", "004"]
```

Each criterion names which case IDs it's graded against — not every criterion applies to every case (e.g. "flags destructive action" is meaningless for a case that has nothing destructive in it).

### 12.4 The grader is itself an agent — with the same honesty problem that implies

Write `eval-grader.chatmode.md`: given a case's input, its answer key, the rubric, and the target agent's actual output, it scores each applicable criterion pass/fail with a one-line justification. This is necessary because rubric grading against free-form text can't be done with a regex — but be clear-eyed about the limitation: a judge model can be fooled by confident-sounding but wrong output in much the same way a human skimming quickly can. Treat automated grading as a **first-pass filter that catches obvious regressions**, not a substitute for a human periodically reading actual `spec.md` outputs from real features and checking they still feel like the rigorous, challenging document §3 describes. Schedule that human spot-check explicitly — e.g. one real spec reviewed by a human per month — rather than assuming the automated eval is sufficient on its own.

### 12.5 `scripts/run-agent-evals.sh` and when it runs

This script, for a given agent: runs each case's input through that agent's chatmode (in an isolated sandbox — never against a real issue or the live Projects board), captures the output, runs it through `eval-grader.chatmode.md`, and appends a result line to `evals/results/<agent>-<date>.json` (pass/fail per criterion, per case).

Be realistic about automation here rather than assuming this slots into a normal CI job: chatmodes are Copilot agent-mode/cloud-agent prompts, not standalone executables, so "run this in a GitHub Actions runner on every PR" may not be straightforward depending on current Copilot tooling. The practical version of this gate is: trigger `run-agent-evals.sh` as a manually-invoked Copilot cloud agent task (or a scheduled automation, per §5.1) whenever a PR touches `.github/chatmodes/**` or `.github/instructions/**`, rather than assuming it can run unattended in `ci.yml` the same way `check-agent-boundaries.sh` does. Confirm what's actually feasible in your Copilot plan/tooling before committing to "blocks the PR" as opposed to "must be run and reviewed before merge."

### 12.6 Regression gate

Record each eval run's pass rate per agent in `evals/results/`. Before merging a change to any `.chatmode.md` or `.instructions.md` file, the new pass rate must be **at or above** the last recorded baseline for that agent — a drop is treated the same as a failing test, and should block merge (or at minimum require an explicit human override with a stated reason, logged in the PR) exactly as a `check-agent-boundaries.sh` failure would.

---

## 13. Build order for the AI executing this spec

1. Scaffold the directory structure in §1, including `.github/agent-boundaries.yml`, `.github/automations/`, `.github/workflows/add-to-project.yml` and `chain-health.yml`, `docs/ops/`, and the new `scripts/` entries.
2. Create the `feature-chain-automation` GitHub App (§11.2), install it on this repo with the minimal permissions listed there, store its App ID and private key as repository secrets, and record it in `docs/ops/bot-identity.md`.
3. Write `scripts/setup-github-project.sh` and run it once, under a human's own `gh auth` (§11.4 — not the App), to create the Projects (v2) board and its four fields — record the project number in `github-workflow.instructions.md`.
4. Write `scripts/update-ticket-stage.sh`, `scripts/log-agent-run.sh`, and `scripts/check-agent-boundaries.sh`.
5. Write `.github/agent-boundaries.yml` (§9.1) and `.github/ISSUE_TEMPLATE/feature-request.yml` and `.github/workflows/add-to-project.yml` (using the App token per §11.2/§11.3).
6. Write `.github/copilot-instructions.md`.
7. Write `github-workflow.instructions.md` (ticket handling, idempotency, commit-tagging, and telemetry-logging mechanics) plus the other scoped `.instructions.md` files and `security.instructions.md`.
8. Write the six `.chatmode.md` files from §3, each referencing `github-workflow.instructions.md`, implementing §6.2's idempotency checks, §9.2's commit tagging, and §10.1's telemetry logging.
9. Write `eval-grader.chatmode.md`, then write at least the four starter eval cases per agent from §12.2 and each agent's `rubric.yml`, and write `scripts/run-agent-evals.sh`. Run the eval suite once against the freshly-written chatmodes before using any of them on a real feature, and record the baseline pass rate.
10. Write `new-feature.prompt.md`, then configure the Copilot cloud agent automations from §5.2 (each including the §5.5 pause/circuit-breaker checks), and record each in `.github/automations/README.md`.
11. Wire `ci.yml` to run lint/tests/secret-scan **and** `scripts/check-agent-boundaries.sh` on every push/PR, wire `chain-health.yml` (using the App token) on a schedule, and set up `deploy-staging.yml` / `deploy-prod.yml` per §7/§8.
12. Do a dry run on one small, low-risk feature end-to-end — confirm the issue gets created, the board updates at every stage, automations fire without manual commands, a re-triggered automation doesn't double-act, a deliberately-introduced boundary violation actually fails CI, and the three human checkpoints pause the chain — before trusting it on anything touching auth, payments, or PII.
13. Deliberately force three consecutive failures on one stage in a test feature to confirm the circuit breaker trips and posts to the issue rather than looping forever, and confirm `docs/ops/CHAIN_PAUSED` actually halts every agent and automation when added.
14. Run a second feature concurrently with the first as a deliberate isolation test (§6.1) before considering the chain production-ready for multiple simultaneous features.
15. Confirm the App-based token (not a personal PAT) is genuinely what `add-to-project.yml` and `chain-health.yml` use in practice — e.g. by temporarily revoking a maintainer's personal `gh auth` and confirming those workflows still run.
16. Put a recurring reminder in place (e.g. a monthly calendar item, not another automation) for the human spot-check from §12.4 — the eval loop catches regressions, but only a human reading real output periodically catches the agent quietly getting worse in a way the rubric doesn't cover.
