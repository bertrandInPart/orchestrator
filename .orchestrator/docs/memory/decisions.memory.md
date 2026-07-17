# Decisions memory

Accumulated architecture decisions from past features, read by the Architect agent before
designing a new feature so it doesn't contradict or duplicate a prior decision. Individual
feature-specific ADRs live in `.orchestrator/docs/features/<slug>/adr-*.md`; this file is a running index/summary
of the ones worth surfacing across features.

Format:

```
## <YYYY-MM-DD> — <short title> (feature: <slug>)
**Decision:** <what was decided>
**Why:** <one or two sentences of rationale>
**See also:** .orchestrator/docs/features/<slug>/adr-<n>.md
```

---

*(no entries yet — this file is seeded empty; the first Architect run that makes a decision
worth remembering should add it here)*
