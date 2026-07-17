# Case 003 — Genuinely trivial feature

## Input (what the Spec Writer agent receives)

> Feature name: "Show app version in footer"
> Description: "Display the current app version number (e.g. 'v1.4.2') in small text in the page
> footer, sourced from package.json, visible on every page."
> Requester: self
> Priority: Low

## Answer key — a good spec.md for this case must

- Have an Open Questions section that is empty or contains at most one genuinely minor question
  (e.g. exact placement/styling) — this feature has essentially no real ambiguity, and an agent
  that manufactures several open questions here (e.g. "should this support multiple languages?",
  "should this be clickable?") is over-interrogating a simple request, not being thorough.
- Still cover the basic states relevant to this feature (e.g. what happens if the version can't be
  read — though for a build-time constant this may reasonably be "not applicable, explain why").
- NOT invent edge cases from categories that are genuinely inapplicable (e.g. concurrency/race
  conditions make no sense for a static, non-interactive footer label) — if it lists such a
  category, it should explicitly say why it doesn't apply rather than forcing a bullet into it.
- NOT propose implementation detail (e.g. "read `require('../../package.json').version`").
