# Skill: Drift check (artifact freshness)

Downstream stages rely on upstream planning artifacts (`spec.md`, `architecture.md`) staying frozen
once their owning stage hands off. If a human — or an agent re-run — edits one of those files
afterward, everything built against the old version is now silently based on stale content. This
check exists to catch that instead of letting it pass unnoticed.

## Recording a hash (every agent, at DoD-pass time, for your own primary output file(s))

When you append your `DoD: PASS` entry to the lifecycle file (see
[`lifecycle-file.skill.md`](lifecycle-file.skill.md)), also append one line per primary output
file you're handing off:

```markdown
- **Artifact hash:** `.orchestrator/docs/features/<slug>/<file>.md` = `sha256:<hex digest>`
```

Compute the digest over the file's exact current bytes. This is "the content I'm freezing and
handing off," recorded as a normal append-only lifecycle entry — nothing to maintain separately.

## Checking for drift (every agent, at DoR-check time, for every upstream file you depend on)

1. For each upstream file you read as part of your DoR check (per `context-scope.skill.md`'s read
   list) that has a prior `Artifact hash` line anywhere in the lifecycle file: recompute its hash
   now and compare to the **most recent** recorded hash for that exact path (scan the lifecycle
   file bottom-up — the first match you hit is the current baseline; don't trust any cached
   summary, since the file is append-only and this is always derivable from the log itself).
2. **Match:** no drift. Proceed with the rest of your DoR check normally.
3. **Mismatch:** this is a DoR failure, but a distinct kind worth naming — the file wasn't wrong
   when it was written, it was edited *after* its owning stage already handed it off. Follow the
   normal callback rule in [`dor-check.skill.md`](dor-check.skill.md), but say so explicitly in the
   callback comment: *"`<file>` changed after your DoD passed on `<date>` — please confirm this
   edit is intentional and, if so, complete your stage again so the recorded hash and the file
   agree."* Once that callback happens, a fresh `Artifact hash` line gets appended either way, so
   the next check compares against the current baseline rather than re-discovering the same stale
   mismatch forever.
4. **No baseline exists yet:** nobody has recorded a hash for that file (e.g. this check is being
   adopted on a feature already mid-flight). Record one now and proceed — there's nothing to
   compare against yet, so this isn't drift, just a first observation.

## Where this applies today

- **Architect's DoR** — checks `spec.md` against the hash Spec Writer recorded at its own DoD.
- **Backend Builder's and Frontend Builder's DoR** — check `architecture.md` against the hash
  Architect recorded at its own DoD.

Extend the same mechanic to any other stage/file pair where an upstream planning artifact is meant
to stay frozen — nothing here is specific to spec.md or architecture.md, just applied to those two
today because they're the artifacts every downstream stage builds against most heavily.
