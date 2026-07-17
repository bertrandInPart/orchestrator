# Skill: Context scope

Loading the wrong amount of context costs you twice: too little and you make decisions on
incomplete information; too much and signal drowns in noise (and you burn budget re-reading
things irrelevant to the decision in front of you). This skill states, per stage, exactly what to
read — and calls out what NOT to read even if it's tempting.

## Per-stage reading list

| Agent | Read | Do NOT read |
|---|---|---|
| **spec-writer** | The raw request or issue thread; `.orchestrator/docs/memory/conventions.memory.md`; **targeted** reads of existing `server/**`/`client/**` code in this feature's specific domain (see "Grounding spec-writer's context" below) | Full architecture.md/code of *unrelated* features, or a broad codebase tour — you're verifying facts about the area this request touches, not researching implementation options |
| **architect** | `spec.md` in full; the issue thread's human answers; the *relevant section(s)* of `.orchestrator/docs/memory/decisions.memory.md` (see "Large shared files" below) | Other features' `spec.md`/`architecture.md` unless `decisions.memory.md` explicitly points you at one as precedent |
| **backend-builder** | `architecture.md` (API contract + your components); `.github/instructions/backend.instructions.md`; `.github/instructions/data.instructions.md` | Anything under `client/**`; other features' notes files |
| **frontend-builder** | `architecture.md` (API contract + your components); `.github/instructions/frontend.instructions.md` | Anything under `server/**` or schema files; other features' notes files |
| **test-engineer** | `spec.md` (acceptance criteria + edge cases); `architecture.md`; `backend-notes.md`; `frontend-notes.md`; `.github/instructions/testing.instructions.md` | Implementation source files beyond what's needed to understand the public surface you're testing against — test to spec, not to internals |
| **reviewer** | The full diff on the feature branch; `.github/instructions/security.instructions.md` | Other open features' diffs — review this feature's diff only |
| **release-engineer** | Everything in `.orchestrator/docs/features/<slug>/` (all of it — you're the one stage whose job is genuine end-to-end synthesis) | Other features' `.orchestrator/docs/features/<other-slug>/` directories |

If your stage needs something outside your own row above, that's a signal worth naming explicitly
in your completion comment (e.g. "needed to check X outside normal scope because Y") rather than
silently expanding your own reading habits going forward.

## Large shared files: search, don't load whole

`.orchestrator/docs/memory/decisions.memory.md` and `.orchestrator/docs/memory/conventions.memory.md` grow forever — every
feature appends to them. Loading either file in full, every run, is exactly the "more than you
need" failure mode this skill exists to prevent.

- Use grep/search for keywords from the current feature's domain (entity names, the area of the
  app it touches, e.g. "auth", "notifications", "billing") rather than reading the file
  top-to-bottom.
- Only fall back to reading the whole file if a targeted search comes up empty and you have a
  specific reason to suspect relevant precedent exists (e.g. the spec explicitly says "similar to
  the X feature").
- When you do append a new entry to either memory file, append it — don't rewrite or reorganize
  existing entries as a side effect of your own work.

## Within a single large file, read the section you need

`architecture.md`, `spec.md`, and the lifecycle file can all get long on a complex feature.
Prefer jumping to the specific section header relevant to your current question (e.g. Backend
Builder jumping straight to "API contract" and "Migration notes", not re-reading the whole UX
Walkthrough section that Frontend Builder owns) over reading start to finish every time you need
one fact from it.

## Grounding spec-writer's context (verifying facts vs. designing)

Spec Writer's "don't read other features' code" rule (above) is about not *designing* off
implementation precedent — it is not license to write a spec against a mental model of the app
that's stale or simply wrong. If a feature request touches an area of the app that already has
code (`server/**`, `client/**`), a spec that gets the *current* behavior wrong is worse than one
with an open question, because it looks confident while being incorrect.

The distinction that keeps this from turning into implementation-detail creep:

- **Verifying a fact about what exists today** (does a search field already exist on this list?
  what fields does this schema actually have? does this permission check currently exist?) is
  in scope, done with a narrow, targeted grep/glob for the specific entity/route/component names
  implied by the request — not a broad tour of the codebase, and not reading code from a
  *different* feature area than the one the request touches.
- **Proposing how something should be built** (which library, which route shape, which schema
  field) stays out of scope regardless of what you found in the code. You're reading to describe
  the *current* state accurately in the spec, not to sketch the *future* state.

If a targeted check turns up nothing (the domain has no code yet — greenfield), say so explicitly
and move on; there's nothing to reconcile. If it turns up code that **contradicts**
`.orchestrator/docs/memory/conventions.memory.md`, contradicts what the requester assumed, or is genuinely
ambiguous even after reading it, treat the code as the ground truth for "what currently exists"
(memory can be stale; the running app's code can't be) — and raise the discrepancy as a
**Context** open question for the human, distinct from an ordinary scope question, per
`spec-writer.chatmode.md`'s "Context grounding pass."
